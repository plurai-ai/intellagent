import os.path

from simulator.env import Env
from simulator.agents_graphs.dialog_graph import Dialog
from simulator.agents_graphs.langgraph_tool import AgentTools
import re
from langchain_core.messages import AIMessage
from simulator.utils.llm_utils import get_llm, set_callback, get_prompt_template, set_llm_chain
from simulator.dataset.events_generator import Event
import uuid
from simulator.utils.sqlite_handler import SqliteSaver
from simulator.utils.parallelism import async_batch_invoke
from simulator.dialog.utils import intermediate_processing
from simulator.utils.logger_config import get_logger, ConsoleColor

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
        self.config = config
        self.llm_user = get_llm(config['llm_user'])
        self.llm_user = self.llm_user | self.get_user_parsing_function(
            parsing_mode=config['user_parsing_mode'])  # The user language model
        self.callbacks = [set_callback(t) for t in
                          {config['llm_user']['type'], config['llm_chat']['type']}]  # The callbacks
        self.data = {}
        self.data_examples = environment.data_examples
        self.data_schema = environment.data_schema
        self.env_tools = environment.tools
        self.env_tools_schema = None
        self.dialog = None
        self.environment_prompt = environment.prompt
        if environment.tools_schema is not None and environment.tools_schema:
            self.env_tools_schema = environment.tools_schema
        self.set_critique()
        self.chatbot = None
        self.chatbot_initial_messages = None

    def set_critique(self):
        # set the critique model
        critique_config = self.config['critique_config']
        self.llm_critique = get_llm(critique_config['llm'])
        critique_prompt = get_prompt_template(critique_config['prompt'])
        critique_prompt = critique_prompt.partial(prompt=self.environment_prompt)
        self.llm_critique = critique_prompt | self.llm_critique

    def get_user_parsing_function(self, parsing_mode='default'):
        def parse_user_message(ai_message: AIMessage) -> dict[str, str]:
            """Parse the user message."""
            extracted_text = ai_message.content
            extracted_thought = ''
            if parsing_mode == 'thought':
                pattern = r"^(.*?)\s*User Response:\s*(.*)"  # The pattern to extract the user response
                match = re.search(pattern, ai_message.content, re.DOTALL)
                if match:
                    extracted_thought = match.group(1).strip()  # Text before "User Response:"
                    extracted_text = match.group(2).strip()
                else:
                    extracted_text = ai_message.content
            return {'response': extracted_text, 'thought': extracted_thought}

        return parse_user_message

    def set_agent_tool_chatbot(self, chatbot_prompt_params=None):
        """
        Setting the default agent tool chatbot (llm with function calling)
        :param chatbot_prompt_params: The parameters for the chatbot prompt.
        """
        chatbot_prompt_params = chatbot_prompt_params if chatbot_prompt_params is not None else {}
        llm_chat = get_llm(self.config['llm_chat'])
        self.chatbot = AgentTools(llm=llm_chat, tools=self.env_tools, tools_schema=self.env_tools_schema)
        if self.chatbot_initial_messages is None:
            chatbot_prompt_args = {'from_str': {'template': self.environment_prompt}}
            chatbot_prompt = get_prompt_template(chatbot_prompt_args)
            chatbot_messages = chatbot_prompt.format_messages(**chatbot_prompt_params)
            if len(chatbot_messages) == 1:
                chatbot_messages.append(AIMessage(content="Hello! 👋 I'm here to help with any request you might have."))
            self.chatbot_initial_messages = chatbot_messages

    def init_dialog(self, experiment_path: str):
        """
        Initialize the dialog graph.
        :param experiment_path: The path of the experiment.
        """
        self.memory = SqliteSaver(os.path.join(experiment_path, 'memory.db'))
        if self.chatbot is None:
            self.set_agent_tool_chatbot()  # Set the default agent chatbot
        if self.chatbot_initial_messages is None:
            logger = get_logger()
            logger.warning(
                f"{ConsoleColor.RED}Initial messages for the chatbot were not provided. "
                f"Using empty list{ConsoleColor.RESET}")
            self.chatbot_initial_messages = []

        self.dialog = Dialog(self.llm_user, self.chatbot, critique=self.llm_critique,
                             intermediate_processing=intermediate_processing,
                             memory=self.memory)
        self.user_prompt = get_prompt_template(self.config['user_prompt'])

    def run(self, user_prompt_params=None, chatbot_env_args=None):
        """
        Run the simulation.
        :param user_prompt_params: The parameters for the user prompt.
        :param chatbot_env_args: The arguments for the chatbot environment, for example db setting for the scenario
        """
        if self.dialog is None:
            raise ValueError("The dialog is not initialized. Please run init_dialog first.")
        user_prompt_params = user_prompt_params if user_prompt_params is not None else {}
        user_messages = self.user_prompt.format_messages(**user_prompt_params)
        recursion_limit = self.config.get('recursion_limit', 25)
        return self.dialog.invoke(input={"user_messages": user_messages,
                                         "chatbot_messages": self.chatbot_initial_messages,
                                         "chatbot_args": chatbot_env_args,
                                         "thread_id": str(uuid.uuid4()),
                                         "user_thoughts": []}, config={'recursion_limit': recursion_limit})

    async def arun(self, user_prompt_params=None, chatbot_env_args=None):
        """
        Run the simulation asynchronously.
        :param user_prompt_params:
        :param chatbot_env_args:
        :return:
        """
        if self.dialog is None:
            raise ValueError("The dialog is not initialized. Please run init_dialog first.")
        user_prompt_params = user_prompt_params if user_prompt_params is not None else {}
        user_messages = self.user_prompt.format_messages(**user_prompt_params)
        recursion_limit = self.config.get('recursion_limit', 25)
        return await self.dialog.ainvoke(input={"user_messages": user_messages,
                                                "chatbot_messages": self.chatbot_initial_messages,
                                                "chatbot_args": chatbot_env_args,
                                                "thread_id": str(uuid.uuid4()),
                                                "user_thoughts": []}, config={'recursion_limit': recursion_limit})

    def run_event(self, event: Event):
        """
        Run the dialog between the user and the chatbot on the event.
        :param event: The event to run.
        """
        return self.run(user_prompt_params={'scenario': event.scenario,
                                            'rows': event.relevant_rows,
                                            'expected_behaviour': event.description.expected_behaviour},
                        chatbot_env_args={'data': event.database})

    async def arun_event(self, event: Event):
        """
        Run the dialog between the user and the chatbot on the event asynchronously.
        :param event: The event to run.
        """
        return await self.arun(user_prompt_params={'scenario': event.scenario,
                                                   'rows': event.relevant_rows,
                                                   'expected_behaviour': event.description.expected_behaviour},
                               chatbot_env_args={'data': event.database})

    def run_events(self, events: list[Event]):
        """
        Run the dialog between the user and the chatbot on the events.
        :param events: The events to run.
        """
        res = async_batch_invoke(self.arun_event, events, num_workers=self.config['num_workers'],
                                 callbacks=self.callbacks, timeout=self.config['timeout'])
        final_result = [{'res': r['result'], 'event_id': events[r['index']].id} for r in res if r['error'] is None]
        cost = sum([r['usage'] for r in res if r['error'] is None])
        return final_result, cost
