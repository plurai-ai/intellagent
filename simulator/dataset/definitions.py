from pydantic import BaseModel, Field
from typing import Annotated, List
from langchain_core.tools import tool
from dataclasses import dataclass
import pandas as pd
from simulator.dataset.descriptor_generator import Description
from simulator.healthcare_analytics import ExceptionEvent, track_event


class row_info(BaseModel):
    table_name: str = Field(description="The table name")
    row: str = Field(
        description="The row to insert to the table, with variables to be replaced, and should be consistent across the rows and tables. Expected format ")


class info_symbolic(BaseModel):
    variables_list: List[str] = Field(description="The list of the symbolic variables and their descriptions")
    enriched_scenario: str = Field(description="The enriched scenario with the symbolic variables")
    symbolic_relations: List[str] = Field(description="The relations between the symbolic variables")
    tables_rows: List[row_info] = Field(description="The rows to insert to the tables. You must insert them according to the insertrion order")


@tool
def calculate(expression: str) -> str:
    """Calculate the result of a mathematical expression. The mathematical expression to calculate, such as '2 + 2'. The expression can contain numbers, operators (+, -, *, /), parentheses, and spaces."""
    if not all(char in "0123456789+-*/(). " for char in expression):
        return "Error: invalid characters in expression"
    try:
        return str(round(float(eval(expression, {"__builtins__": None}, {})), 2))
    except Exception as e:
        track_event(ExceptionEvent(exception_type=type(e).__name__,
                                   error_message=str(e)))
        return f"Error: {e}"


@tool
def think(thought: str) -> str:
    "Use the tool to think about something. It will not obtain new information or change the database, but just append the thought to the log. Use it when complex reasoning is needed."
    return ""


@dataclass
class Event:
    """
    The event
    """
    description: Description
    database: dict[pd.DataFrame]
    scenario: str = None  # The full scenario
    relevant_rows: List[str] = None  # The relevant rows
    id: int = -1  # The id of the event


class FinalResult(BaseModel):
    scenario: str = Field(description="The scenario with the symbolic variables replaced with their values")


@dataclass
class EventSymbolic:
    """
    The symbolic_representation of the event
    """
    description: Description
    symbolic_info: info_symbolic
    policies_constraints: str = None  # The policy constraints

    def __str__(self):
        symbolic_dict = self.symbolic_info.dict()
        tables_rows_str = '\n- '.join([f"Table: {s['table_name']}. Row: {s['row']}" for s in
                                       symbolic_dict['tables_rows']])
        symbolic_relations_str = '\n'.join(symbolic_dict['symbolic_relations'])
        return f"## Enriched scenario:\n{symbolic_dict['enriched_scenario']}\n## Tables rows:\n- {tables_rows_str}\n## Symbolic variable relations:\n{symbolic_relations_str}"
