from langchain_core.language_models.chat_models import BaseChatModel
from simulator.env import Env
from simulator.utils import set_llm_chain, get_prompt_template
from simulator.simulator_graph import Simulator
from agents.langgraph_tool import AgentTools
import re
from langchain_core.messages import AIMessage


class SimulatorExecutor:
    """
    This class is responsible for executing rollout of simulation.
    """

    def __init__(self, llm: BaseChatModel, env: Env):
        """
        Initialize the event generator.
        :param llm (BaseChatModel): The language model to use.
        :param env (Env): The environment of the simulator.
        """
        self.simulator = None
        self.llm = llm
        self.user_llm = llm | self.get_user_parsing_function(
            parsing_mode=env.user_prompt_args.get('parsing_mode', 'default'))
        self.data = {}
        self.data_examples = env.data_examples
        self.data_schema = env.data_schema
        self.env_tools = env.tools
        self.env_tools_schema = None
        if env.tools_schema is not None and env.tools_schema:
            self.env_tools_schema = env.tools_schema
        self.init_simulator(chatbot_prompt_args=env.chatbot_prompt_args, user_prompt_args=env.user_prompt_args)

    def get_user_parsing_function(self, parsing_mode='default'):
        def parse_user_message(ai_message: AIMessage) -> str:
            """Parse the user message."""
            extracted_text = ai_message.content
            if parsing_mode == 'thought':
                pattern = r"User Response:(?:\s?\n)?(.*)"  # The pattern to extract the user response
                match = re.search(pattern, ai_message.content, re.DOTALL)
                if match:
                    extracted_text = match.group(1).strip()
                else:
                    extracted_text = ai_message.content
            return extracted_text

        return parse_user_message

    def get_intermediate_processing_function(self):
        def intermediate_processing(state):
            """Process the state of the simulator."""
            if '###STOP' in state['chatbot_messages'][-1].content:  # Stop signal from the user
                return True
            return False

        return intermediate_processing

    def init_simulator(self, user_prompt_args=None, chatbot_prompt_args=None):
        """
        Initialize the simulator graph.
        :param user_prompt_args (dict): Either a prompt or a dict with prompt_hub_name should be provided.
        :param chatbot_prompt (dict): Either a prompt or a dict with prompt_hub_name should be provided.
        """
        chatbot = AgentTools(llm=self.llm, tools=self.env_tools, tools_schema=self.env_tools_schema)
        self.simulator = Simulator(self.user_llm, chatbot,
                                   intermediate_processing=self.get_intermediate_processing_function())
        self.user_prompt = get_prompt_template(user_prompt_args)
        self.chatbot_prompt = get_prompt_template(chatbot_prompt_args)

    def run(self, user_prompt_params=None, chatbot_prompt_params=None,
            chatbot_env_args = None):
        """
        Run the simulation.
        :param user_prompt_params: The parameters for the user prompt.
        :param chatbot_prompt_params: The parameters for the chatbot prompt.
        :param chatbot_env_args: The arguments for the chatbot environment, for example db setting for the scenario
        """
        user_prompt_params = user_prompt_params if user_prompt_params is not None else {}
        chatbot_prompt_params = chatbot_prompt_params if chatbot_prompt_params is not None else {}
        user_messages = self.user_prompt.format_messages(**user_prompt_params)
        chatbot_messages = self.chatbot_prompt.format_messages(**chatbot_prompt_params)
        if len(chatbot_messages) == 1:
            chatbot_messages.append(AIMessage(content="Hello! 👋 I'm here to help with any request you might have."))
        self.simulator.invoke(input={"user_messages": user_messages,
                                     "chatbot_messages": chatbot_messages,
                                     "chatbot_args": chatbot_env_args})
