import os.path
from simulator.env import Env
from simulator.utils.llm_utils import get_prompt_template
from agents.dialog_graph import Dialog
from agents.langgraph_tool import AgentTools
from typing import Annotated
from pydantic import BaseModel
from langgraph.prebuilt import InjectedState
from langchain_core.messages import AIMessage
from simulator.utils.llm_utils import get_llm, set_callbck, dataframe_to_string
from simulator.events_generator import Event
import uuid
from simulator.utils.sqlite_handler import SqliteSaver
from simulator.utils.parallelism import batch_invoke
from agents.user_graph import UserAgent


class DialogManager:
    """
    This class is responsible for executing rollout of simulation.
    """

    def __init__(self, config: dict, environment: Env):
        """
        Initialize the event generator.
        :param config: The config of the class
        :param environment (Env): The environment of the dialog.
        """
        self.llm_user = get_llm(config['llm_user'])
        self.llm_chat = get_llm(config['llm_chat'])
        self.callbacks = [set_callbck(t) for t in
                          {config['llm_user']['type'], config['llm_chat']['type']}]  # The callbacks
        self.data = {}
        self.data_examples = environment.data_examples
        self.data_schema = environment.data_schema
        self.env_tools = environment.tools
        self.env_tools_schema = None
        self.dialog = None
        self.environment_prompt = environment.prompt
        self.user_prompt = config['user_prompt']
        self.num_workers = config['num_workers']
        self.timeout = config['timeout']
        self.user_parsing_mode = config.get('user_parsing_mode', 'thought')
        if environment.tools_schema is not None and environment.tools_schema:
            self.env_tools_schema = environment.tools_schema

    def get_intermediate_processing_function(self):
        def intermediate_processing(state):
            """Process the state of the dialog."""
            if '###STOP' in state['chatbot_messages'][-1].content:  # Stop signal from the user
                return True
            return False

        return intermediate_processing

    def init_dialog(self, experiment_path: str):
        """
        Initialize the dialog graph.
        :param experiment_path: The path of the experiment.
        """
        chatbot_prompt_args = {'from_str': {'template': self.environment_prompt}}
        self.memory = SqliteSaver(os.path.join(experiment_path, 'memory.db'))
        chatbot = AgentTools(llm=self.llm_chat, tools=self.env_tools, tools_schema=self.env_tools_schema)
        user = UserAgent(agent=self.llm_user, moderator=chatbot)

        self.dialog = Dialog(user, chatbot,
                             intermediate_processing=self.get_intermediate_processing_function(),
                             memory=self.memory, user_parsing_mode=self.user_parsing_mode)
        self.user_prompt = get_prompt_template(self.user_prompt)
        self.chatbot_prompt = get_prompt_template(chatbot_prompt_args)

    def run(self, user_prompt_params=None, chatbot_prompt_params=None,
            chatbot_env_args=None):
        """
        Run the simulation.
        :param user_prompt_params: The parameters for the user prompt.
        :param chatbot_prompt_params: The parameters for the chatbot prompt.
        :param chatbot_env_args: The arguments for the chatbot environment, for example db setting for the scenario
        """
        if self.dialog is None:
            raise ValueError("The dialog is not initialized. Please run init_dialog first.")
        user_prompt_params = user_prompt_params if user_prompt_params is not None else {}
        chatbot_prompt_params = chatbot_prompt_params if chatbot_prompt_params is not None else {}
        user_messages = self.user_prompt.format_messages(**user_prompt_params)
        chatbot_messages = self.chatbot_prompt.format_messages(**chatbot_prompt_params)
        if len(chatbot_messages) == 1:
            chatbot_messages.append(AIMessage(content="Hello! 👋 I'm here to help with any request you might have."))
        return self.dialog.invoke(input={"user_messages": user_messages,
                                         "chatbot_messages": chatbot_messages,
                                         "chatbot_args": chatbot_env_args,
                                         "thread_id": str(uuid.uuid4()),
                                         "user_thoughts": [],
                                         "scenario": user_prompt_params.get('scenario', '')})
    async def arun(self, user_prompt_params=None, chatbot_prompt_params=None,
            chatbot_env_args=None):
        """
        Run the simulation asynchronously.
        :param user_prompt_params:
        :param chatbot_prompt_params:
        :param chatbot_env_args:
        :return:
        """
        if self.dialog is None:
            raise ValueError("The dialog is not initialized. Please run init_dialog first.")
        user_prompt_params = user_prompt_params if user_prompt_params is not None else {}
        chatbot_prompt_params = chatbot_prompt_params if chatbot_prompt_params is not None else {}
        user_messages = self.user_prompt.format_messages(**user_prompt_params)
        chatbot_messages = self.chatbot_prompt.format_messages(**chatbot_prompt_params)
        if len(chatbot_messages) == 1:
            chatbot_messages.append(AIMessage(content="Hello! 👋 I'm here to help with any request you might have."))
        return await self.dialog.ainvoke(input={"user_messages": user_messages,
                                         "chatbot_messages": chatbot_messages,
                                         "chatbot_args": chatbot_env_args,
                                         "thread_id": str(uuid.uuid4()),
                                         "user_thoughts": []})

    def run_event(self, event: Event):
        """
        Run the dialog between the user and the chatbot on the event.
        :param event: The event to run.
        """
        return self.run(user_prompt_params={'scenario': event.scenario,
                                            'expected_behaviour': event.description.expected_behaviour},
                        chatbot_env_args={'data': event.database})

    async def arun_event(self, event: Event):
        """
        Run the dialog between the user and the chatbot on the event asynchronously.
        :param event: The event to run.
        """
        return await self.arun(user_prompt_params={'scenario': event.scenario,
                                            'expected_behaviour': event.description.expected_behaviour},
                        chatbot_env_args={'data': event.database})

    def run_events(self, events: list[Event]):
        """
        Run the dialog between the user and the chatbot on the events.
        :param events: The events to run.
        """
        # res = async_batch_invoke(self.arun_event, events, num_workers=self.num_workers,
        #                          callbacks=self.callbacks, timeout=self.timeout)
        res = batch_invoke(self.run_event, events, num_workers=self.num_workers,callbacks=self.callbacks)
        final_result = [{'res': r['result'], 'event_id':events[r['index']].id} for r in res if r['error'] is None]
        cost = sum([r['usage'] for r in res if r['error'] is None])
        return final_result, cost

    def get_extract_info_function(self, query_info_llm):
        def extract_system_info(query: str, data: Annotated[dict, InjectedState("data")]):
            def dataset_to_str(dataset):
                res_str = ''
                for i,v in dataset.items():
                    res_str += f'Table:{i}\n'
                    res_str += dataframe_to_string(v)
                    res_str += '\n'
                return res_str

            return dataset_to_str(data) #query_info_llm.invoke(input={'query': query, 'dataset': dataset_to_str(data)})
            # try:
            #     return query_info_llm.invoke(input={'query': query, 'dataset': dataset_to_str(dataset)})
            # except Exception as e:
            #     return f"Error: {e}"

        class get_info_input(BaseModel):
            query: str = "The row to insert"

        return extract_system_info, get_info_input