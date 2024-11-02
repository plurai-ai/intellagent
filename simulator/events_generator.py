from agents.langgraph_tool import AgentTools
import pandas as pd
from pydantic import BaseModel
from agents.plan_and_execute import PlanExecuteImplementation
import json
from langchain import hub
from simulator.env import Env
from typing_extensions import Annotated
from langgraph.prebuilt import InjectedState
from langchain_core.tools.structured import StructuredTool
from langchain_core.tools import tool
from langchain_core.language_models.llms import LLM
from simulator.utils import dict_to_str, set_llm_chain
from agents.plan_and_execute import Act, Plan


@tool
def calculate(expression: str) -> str:
    """Calculate the result of a mathematical expression. The mathematical expression to calculate, such as '2 + 2'. The expression can contain numbers, operators (+, -, *, /), parentheses, and spaces."""
    if not all(char in "0123456789+-*/(). " for char in expression):
        return "Error: invalid characters in expression"
    try:
        return str(round(float(eval(expression, {"__builtins__": None}, {})), 2))
    except Exception as e:
        return f"Error: {e}"

@tool
def think(thought: str) -> str:
    "Use the tool to think about something. It will not obtain new information or change the database, but just append the thought to the log. Use it when complex reasoning is needed."
    return ""

class EventSample:
    """
    This class represents an event sample
    """
    def __init__(self, description: str, env: Env):
        self.description = description
        self.schema = env.schema
        self.example = env.example


    def __str__(self):
        return self.event


class EventsGenerator:
    """
    This class is responsible for generating events for the simulator.
    """

    def __init__(self, llm: LLM, env: Env):
        """
        Initialize the event generator.
        :param llm (Runnable): The language model to use.
        :param env (Env): The environment of the simulator.
        """
        self.llm = llm
        self.data = {}
        self.data_examples = env.data_examples
        self.data_schema = env.data_schema
        self.init_agent()

    def init_executors(self) -> dict[AgentTools]:
        """
        Initialize the database plane executors.
        :return: list[AgentTools]: The list of executors.
        """
        rows_data = self.data_examples
        table_insertion_tools = {}
        agent_executors = {}
        for table_name, example in rows_data.items():

            cur_tool, tool_schema = self.get_insertion_function(table_name)
            table_insertion_tools[table_name] = StructuredTool.from_function(
                cur_tool,
                None,
                name='add_row_to_table',
                description='Add a row to the table in json format',
                infer_schema=True,
            )

            system_messages = hub.pull("eladlev/event_executor")
            system_messages = system_messages.format_messages(schema=self.data_schema[table_name],
                                                              example=json.dumps(rows_data[table_name]))
            agent_executor = AgentTools(llm=self.llm, tools=[calculate, think, table_insertion_tools[table_name]],
                                        system_prompt=system_messages)
            agent_executors[table_name] = agent_executor
        return agent_executors

    def get_insertion_function(self, table_name: str):
        def tool_function(json_row: str, dataset: Annotated[dict, InjectedState("dataset")]):
            df = pd.DataFrame([json.loads(json_row)])
            if not table_name in dataset:
                dataset[table_name] = pd.DataFrame()
            dataset[table_name] = pd.concat([dataset[table_name], df], ignore_index=True)
            return f"Added row to {table_name} table"

        class add_row_input(BaseModel):
            json_row: str = "The row to insert"

        return tool_function, add_row_input

    def get_planner_prompt(self):
        prompt = hub.pull("eladlev/planner_event_generator")
        return prompt.partial(tables_info=dict_to_str(self.data_schema))

    def init_agent(self):
        """
        Initialize the agent.
        """
        planner = set_llm_chain(self.llm, prompt=self.get_planner_prompt(), structure=Plan)
        replanner = set_llm_chain(self.llm, prompt_hub_name="eladlev/replanner_event_generator", structure=Act)
        self.agent = PlanExecuteImplementation(planer= planner,
                                               replanner=replanner,
                                               executor=self.init_executors())

    def description_to_event(self, event: str) -> str:
        """
        Generate an event based on the given event.
        """
        return self.agent.invoke(input= {'input':event,'args': {'dataset': {}}})
