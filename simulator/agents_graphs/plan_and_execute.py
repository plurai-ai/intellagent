from typing import Annotated, List, Tuple
from typing_extensions import TypedDict
from pydantic import BaseModel, Field
import operator
from langchain_core.runnables.base import Runnable

from langgraph.graph import END
from langchain import hub
from langgraph.graph import StateGraph, START


class SingleStep(BaseModel):
    """Single step in the plan"""

    content: str = Field(description="The step to execute")
    executor: str = Field(description="Either the table name of the step or if the last step 'Response'")

class Plan(BaseModel):
    """Plan to follow in future"""

    steps: List[SingleStep] = Field(
        description="different steps to follow, should be in sorted order, if no steps are needed then the list should be empty"
    )
    final_response: str = Field(description="The final response to the user")


class PlanExecute(TypedDict):
    input: str
    plan: List[dict]
    past_steps: Annotated[List[Tuple], operator.add]
    response: str
    args: dict


class Response(BaseModel):
    """Response to user."""

    response: str


def should_end(state: PlanExecute):
    if not state["plan"]:
        return END
    else:
        return "agent"


class PlanExecuteImplementation:
    """
    Building the plan and execute graph
    """

    def __init__(self, planner: Runnable, executor: dict[Runnable], replanner: Runnable):
        """
        Initialize the event generator.
        :param planner (Runnable): The planner model
        :param executor (Runnable): The executor model
        :param replanner (Runnable): The replanner model
        """
        self.planner = planner
        self.executor = executor
        self.replanner = replanner
        self.compile_graph()

    def get_replanner_function(self):
        def replan_step(state: PlanExecute):
            output = self.replanner.invoke(state)
            output = output.dict()
            return {"plan": output['steps'], 'response': output['final_response']}
        return replan_step

    def get_planner_function(self):
        def plan_step(state: PlanExecute):
            plan = self.planner.invoke(state['input'])
            return {"plan": plan.dict()['steps'], 'response': plan.dict()['final_response']}
        return plan_step

    def get_executor_function(self):
        def execute_step(state: PlanExecute):
            plan = state["plan"]
            plan_str = "\n".join(f"{i + 1}. {step['content']}" for i, step in enumerate(plan))
            task = plan[0]
            task_formatted = f"""For the following plan:
        {plan_str}\n\nYou are tasked with executing step {1}, {task['content']}."""
            if task['executor']  == 'Response':
                return { "past_steps": [(task['content'],task['content'] )]}
            else:
                agent_response = self.executor[task['executor']].invoke(task_formatted, additional_args=state['args'])
                return {
                    "past_steps": [(task['content'], agent_response["messages"][-1].content)],
                    "args": agent_response["args"]
                }
        return execute_step

    def compile_graph(self):
        workflow = StateGraph(PlanExecute)

        # Add the plan node
        workflow.add_node("planner", self.get_planner_function())

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

    async def ainvoke(self, **kwargs):
        """
        Invoke the agent with the messages
        :return:
        """
        return await self.graph.ainvoke(**kwargs)
