from typing import Annotated, List, Tuple
from typing_extensions import TypedDict
from pydantic import BaseModel, Field
import operator
from langchain_core.runnables.base import Runnable
from langchain_core.language_models.llms import LLM
from langgraph.graph import END
from langchain import hub
from langgraph.graph import StateGraph, START
from typing import Union


class SingleStep(BaseModel):
    """Single step in the plan"""

    content: str = Field(description="The step to execute")
    executor: str = Field(description="The table to executor name")


class Plan(BaseModel):
    """Plan to follow in future"""

    steps: List[SingleStep] = Field(
        description="different steps to follow, should be in sorted order"
    )


class PlanExecute(TypedDict):
    input: str
    plan: List[dict]
    past_steps: Annotated[List[Tuple], operator.add]
    response: str
    args: dict


class Response(BaseModel):
    """Response to user."""

    response: str


class Act(BaseModel):
    """Action to perform."""

    action: Union[Response, Plan] = Field(
        description="Action to perform. If you want to respond to user, use Response. "
                    "If you need to further use tools to get the answer, use Plan."
    )


def should_end(state: PlanExecute):
    if "response" in state and state["response"]:
        return END
    else:
        return "agent"


class PlanExecuteImplementation:
    """
    Building the plan and execute graph
    """

    def __init__(self, planer: Runnable, executor: dict[Runnable], replanner: Runnable):
        """
        Initialize the event generator.
        :param planer (Runnable): The planer model
        :param executor (Runnable): The executor model
        :param replanner (Runnable): The replanner model
        """
        self.planer = planer
        self.executor = executor
        self.replanner = replanner
        self.compile_graph()

    def get_replanner_function(self):
        def replan_step(state: PlanExecute):
            output = self.replanner.invoke(state)
            if isinstance(output.action, Response):
                return {"response": output.action.response}
            else:
                return {"plan": output.action.dict()['steps']}

        return replan_step

    def get_planer_function(self):
        def plan_step(state: PlanExecute):
            plan = self.planner.invoke(state['input'])
            return {"plan": plan.dict()['steps']}
        return plan_step

    def get_executor_function(self):
        def execute_step(state: PlanExecute):
            plan = state["plan"]
            plan_str = "\n".join(f"{i + 1}. {step['content']}" for i, step in enumerate(plan))
            task = plan[0]
            task_formatted = f"""For the following plan:
        {plan_str}\n\nYou are tasked with executing step {1}, {task['content']}."""
            agent_response = self.executor[task['executor']].invoke(task_formatted, additional_args=state['args'])
            return {
                "past_steps": [(task['content'], agent_response["messages"][-1].content)],
                "args": agent_response["args"]
            }

        return execute_step

    def compile_graph(self):
        workflow = StateGraph(PlanExecute)

        # Add the plan node
        workflow.add_node("planner", self.get_planer_function())

        # Add the execution step
        workflow.add_node("agent", self.get_executor_function())

        # Add a replan node
        workflow.add_node("replan", self.get_replanner_function())

        workflow.add_edge(START, "planner")

        # From plan we go to agent
        workflow.add_edge("planner", "agent")

        # From agent, we replan
        workflow.add_edge("agent", "replan")

        workflow.add_conditional_edges(
            "replan",
            # Next, we pass in the function that will determine which node is called next.
            should_end,
            ["agent", END],
        )

        # Finally, we compile it!
        # This compiles it into a LangChain Runnable,
        # meaning you can use it as you would any other runnable
        self.graph = workflow.compile()
    def invoke(self, **kwargs):
        """
        Invoke the agent with the messages
        :return:
        """
        return self.graph.invoke(**kwargs)
