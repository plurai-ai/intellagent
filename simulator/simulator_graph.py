from langchain_core.runnables.base import Runnable
from typing import Callable
from langgraph.graph import END
from typing import Annotated
from langgraph.graph import StateGraph, START
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages
from langchain_core.messages import HumanMessage, AIMessage

class SimState(TypedDict):
    user_messages: Annotated[list, add_messages]
    chatbot_messages: Annotated[list, add_messages]

class Simulator:
    """
    Building the simulator graph that runs the chatbot and the user
    """

    def __init__(self, user: Runnable, chatbot: Runnable, intermediate_processing: Callable = None):
        """
        Initialize the event generator.]
        :param user (Runnable): The user model
        :param chatbot (Runnable): The chatbot model
        :param intermediate_processing (optional): A function between that processes the output of the user and the
        chatbot at each step
        """
        self.user = user
        self.chatbot = chatbot
        self.intermediate_processing = intermediate_processing #TODO: Add default function
        self.compile_graph()

    def get_end_condition(self):
        def should_end(state: SimState):
            terminate = self.intermediate_processing(state)
            if terminate:
                return END
            else:
                return "chatbot"
        return should_end

    def get_user_node(self):
        def simulated_user_node(state):
            messages = state["user_messages"]
            # Call the simulated user
            response = self.user.invoke({"messages": messages})
            # This response is an AI message - we need to flip this to be a human message
            return {"chatbot_messages": [HumanMessage(content=response.content)],
                    'user_messages': [AIMessage(content=response.content)]}
        return simulated_user_node

    def get_chatbot_node(self):
        def chat_bot_node(state):
            messages = state["chatbot_messages"]
            # Call the chatbot
            response = self.chatbot.invoke({"messages": messages})
            return {"chatbot_messages": [AIMessage(content=response.content)],
                    'user_messages': [HumanMessage(content=response.content)]}
        return chat_bot_node

    def compile_graph(self):
        workflow = StateGraph(SimState)
        workflow.add_node("user", self.get_user_node())
        workflow.add_node("chatbot", self.get_chatbot_node())
        workflow.add_edge(START, "user")
        workflow.add_conditional_edges(
            "user",
            self.get_end_condition(),
            ["chatbot", END],
        )
        workflow.add_edge("chatbot", "user")
        self.graph = workflow.compile()
