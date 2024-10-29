from typing import Annotated, List, Tuple
from typing_extensions import TypedDict
from pydantic import BaseModel, Field
import operator
from langchain_core.runnables.base import Runnable
from typing import Literal
from langchain_core.prompts import HumanMessagePromptTemplate, SystemMessagePromptTemplate, AIMessagePromptTemplate
from langchain_core.language_models.llms import LLM
from langgraph.graph import END
from langchain import hub
from langgraph.graph import StateGraph, START
from langchain_core.prompts import ChatPromptTemplate
from typing import Union


class SingleStep(BaseModel):
    """Single step in the plan"""

    step: str = Field(description="The step to execute")
    table: str = Field(description="The table to execute the step on")


class Plan(BaseModel):
    """Plan to follow in future"""

    steps: List[SingleStep] = Field(
        description="different steps to follow, should be in sorted order"
    )


class PlanExecute(TypedDict):
    input: str
    plan: List[str]
    past_steps: Annotated[List[Tuple], operator.add]
    response: str


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

    def __init__(self, planer: Runnable = None, executor: Runnable = None, replanner: Runnable = None):
        """
        Initialize the event generator.]
        :param planer (Runnable): The planer model
        :param executor (Runnable): The executor model
        :param replanner (Runnable): The replanner model
        """
        self.planer = planer
        self.executor = executor
        self.replanner = replanner

    def set_replanner(self, system_prompt: str, llm: LLM):
        """
        Set the replanner from a system prompt
        :param system_prompt: The system prompt for the replanner
        :param llm (LLM): The LLM model
        """
        replanner_prompt = hub.pull("eladlev/replanner")
        messages = [
            SystemMessagePromptTemplate.from_template(system_prompt),
            replanner_prompt.messages[0],
        ]
        replanner_template = ChatPromptTemplate.from_messages(messages)
        self.replanner = replanner_template | llm.with_structured_output(Act)

    def set_planner(self, llm: LLM, **kwargs):
        """
        Set the planner from a langchain prompt name. Expecting either prompt or prompt_hub_name and prompt_hub_key
        :param llm (LLM): The LLM model
        """
        if "prompt_hub_name" in kwargs:
            hub_key = kwargs.get("prompt_hub_key", None)
            planner_template = hub.pull(kwargs["prompt_hub_name"], api_key=hub_key)
        elif "prompt" in kwargs:
            planner_template = kwargs["prompt"]
        else:
            raise ValueError("Either prompt or prompt_hub_name should be provided")

        self.planner = planner_template | llm.with_structured_output(Plan)

    def get_replanner_function(self):
        async def replan_step(state: PlanExecute):
            output = await self.replanner.ainvoke(state)
            if isinstance(output.action, Response):
                return {"response": output.action.response}
            else:
                return {"plan": output.action.steps}

        return replan_step

    def get_planer_function(self):
        async def plan_step(state: PlanExecute):
            plan = await self.planner.ainvoke({"messages": [("user", state["input"])]})
            return {"plan": plan.steps}

        return plan_step

    def get_executor_function(self):
        async def execute_step(state: PlanExecute):
            plan = state["plan"]
            plan_str = "\n".join(f"{i + 1}. {step}" for i, step in enumerate(plan))
            task = plan[0]
            task_formatted = f"""For the following plan:
        {plan_str}\n\nYou are tasked with executing step {1}, {task}."""
            agent_response = await self.executor.ainvoke(
                {"messages": [("user", task_formatted)]}
            )
            return {
                "past_steps": [(task, agent_response["messages"][-1].content)],
            }

        return execute_step

    def compile_graph(self):
        workflow = StateGraph(PlanExecute)

        # Add the plan node
        workflow.add_node("planner", self.get_replanner_function())

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
