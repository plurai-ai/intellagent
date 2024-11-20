from typing import Annotated, List, Tuple
from typing_extensions import TypedDict
from langchain_core.runnables.base import Runnable
from langgraph.graph import END
from langgraph.graph import StateGraph, START
from langgraph.graph.message import add_messages
from langchain_core.messages import (
    AIMessage,
    AnyMessage,
    ToolCall,
    ToolMessage,
)
from simulator.utils.llm_utils import get_llm
from simulator.utils.llm_utils import get_prompt_template


class RefineState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    scenario: str
    args: dict
    feedback_message: str


def should_end(state: RefineState):
    if state["feedback_message"] == '':
        return END
    else:
        return "agent"

def should_moderate(state: RefineState):
    if state["feedback_message"] == '':
        return "agent"
    else:
        return "feedback"


class UserAgent:
    """
    Building the user agent graph
    """

    def __init__(self, agent: Runnable, moderator: Runnable):
        """
        Initialize the agent
        :param agent (Runnable): The planner model
        :param moderator (Runnable): The executor model
        """
        self.agent = agent
        self.database_moderator = moderator
        self.compile_graph()

    def get_verifier_function(self):
        llm = get_llm({'type': 'azure', 'name': 'gpt-4o-mini'})
        prompt = get_prompt_template({'prompt_hub_name': 'eladlev/user_verifier'})
        verifier_llm = prompt | llm

        def verifier_step(state: RefineState):
            output = verifier_llm.invoke(state['messages'])
            output = output.dict()
            return {"plan": output['steps'], 'response': output['final_response']}
        return verifier_step

    def get_agent_function(self):
        def agent_step(state: RefineState):
            output = self.agent.invoke(state['messages'])
            output = output.dict()
            return {"plan": output['steps'], 'response': output['final_response']}
        return agent_step

    def get_moderator_function(self):
        def feedback_step(state: RefineState):
            output = self.moderator.invoke(state['input'])
            return {"plan": plan.dict()['steps'], 'response': plan.dict()['final_response']}
        return feedback_step


    def compile_graph(self):
        workflow = StateGraph(RefineState)

        # Define the nodes we will cycle between
        workflow.add_node("agent", self.get_agent_function())  # agent
        workflow.add_node('verifier', self.get_verifier_function())  # verifier
        workflow.add_node("feedback", self.get_moderator_function())  # Re-writing the question

        workflow.add_edge(START, "agent")
        workflow.add_edge("agent", "verifier")
        workflow.add_conditional_edges("verifier", should_moderate, ["feedback", END])
        workflow.add_edge("agent", "feedback")

        workflow.add_conditional_edges(
            "feedback",
            # Next, we pass in the function that will determine which node is called next.
            should_end,
            ["agent", END],
        )

        self.graph = workflow.compile()


    def invoke(self, messages=None, config=None, additional_args=None):
        """Invoke the agent with the messages
        :param messages: The messages to invoke the agent with
        :param config: The configuration for the agent
        :param additional_args: Additional args arguments for the agent
        """
        return self.graph.invoke({'messages': messages, 'args': additional_args, 'feedback_message': ''}, config=config)
