from simulator.env import Env
from simulator.utils import get_prompt_template
from simulator.dialog_graph import Dialog
from agents.langgraph_tool import AgentTools
import re
from langchain_core.messages import AIMessage
from simulator.utils import get_llm


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
        self.llm = get_llm(config['llm'])
        self.user_llm = self.llm | self.get_user_parsing_function(
            parsing_mode=config['user_parsing_mode'])  # The user language model
        self.data = {}
        self.data_examples = environment.data_examples
        self.data_schema = environment.data_schema
        self.env_tools = environment.tools
        self.env_tools_schema = None
        if environment.tools_schema is not None and environment.tools_schema:
            self.env_tools_schema = environment.tools_schema
        self.init_dialog(chatbot_prompt_args={'prompt': environment.prompt}, user_prompt_args=config['user_prompt'])

    def get_user_parsing_function(self, parsing_mode='default'):
        def parse_user_message(ai_message: AIMessage) -> str:
            """Parse the user message."""
            extracted_text = ai_message.content
            if parsing_mode == 'thought':
                pattern = r"^(.*?)\s*User Response:\s*(.*)"  # The pattern to extract the user response
                match = re.search(pattern, ai_message.content, re.DOTALL)
                if match:
                    extracted_thought = match.group(1).strip()  # Text before "User Response:"
                    extracted_text = match.group(2).strip()
                else:
                    extracted_text = ai_message.content
            return extracted_text

        return parse_user_message

    def get_intermediate_processing_function(self):
        def intermediate_processing(state):
            """Process the state of the dialog."""
            if '###STOP' in state['chatbot_messages'][-1].content:  # Stop signal from the user
                return True
            return False

        return intermediate_processing

    def init_dialog(self, user_prompt_args=None, chatbot_prompt_args=None):
        """
        Initialize the dialog graph.
        :param user_prompt_args (dict): Either a prompt or a dict with prompt_hub_name should be provided.
        :param chatbot_prompt (dict): Either a prompt or a dict with prompt_hub_name should be provided.
        """
        chatbot = AgentTools(llm=self.llm, tools=self.env_tools, tools_schema=self.env_tools_schema)
        self.dialog = Dialog(self.user_llm, chatbot,
                             intermediate_processing=self.get_intermediate_processing_function())
        self.dialog.output_path = '/Users/eladl/Documents/Github/chatbot_simulator/output.log'
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
        self.dialog.invoke(input={"user_messages": user_messages,
                                     "chatbot_messages": chatbot_messages,
                                     "chatbot_args": chatbot_env_args})
