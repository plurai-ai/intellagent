from langchain_core.language_models.llms import LLM
from simulator.env import Env
from simulator.utils import set_llm_chain
from simulator.simulator_graph import Simulator
from agents.langgraph_tool import AgentTools

class SimulatorExecutor:
    """
    This class is responsible for executing rollout of simulation.
    """

    def __init__(self, llm: LLM, env: Env):
        """
        Initialize the event generator.
        :param llm (Runnable): The language model to use.
        :param env (Env): The environment of the simulator.
        """
        self.simulator = None
        self.llm = llm
        self.data = {}
        self.data_examples = env.data_examples
        self.data_schema = env.data_schema
        self.env_tools = env.tools
        self.init_simulator()


    def init_simulator(self, user_args=None, chatbot_args=None):
        """
        Initialize the simulator graph.
        :param user_args: The user arguments (if None load default)
        :param chatbot_args: The system arguments (if None load default)
        """
        user_args = user_args if user_args is not None else {'prompt_hub_name': 'eladlev/user_sim'}
        chatbot_args = chatbot_args if chatbot_args is not None else {'prompt_hub_name': 'eladlev/chatbot_sim'}
        user = set_llm_chain(self.llm, **user_args)
        chatbot = AgentTools(llm=self.llm, tools=self.env_tools, **chatbot_args)
        self.simulator = Simulator(user, chatbot)

