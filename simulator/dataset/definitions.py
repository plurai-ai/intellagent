from pydantic import BaseModel, Field
from typing import Annotated, List
from langchain_core.tools import tool
from dataclasses import dataclass
import pandas as pd
from simulator.dataset.descriptor_generator import Description

class row_info(BaseModel):
    table_name: str = Field(description="The table name")
    row: str = Field(
        description="The row to insert to the table, with variables to be replaced, and should be consistent across the rows and tables. Expected format ")

class info_symbolic(BaseModel):
    variables_list: List[str] = Field(description="The list of the symbolic variables and their descriptions")
    enriched_scenario: str = Field(description="The enriched scenario with the symbolic variables")
    symbolic_relations: List[str] = Field(description="The relations between the symbolic variables")
    tables_rows: List[row_info] = Field(description="The rows to insert to the tables")

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


@dataclass
class Event:
    """
    The event
    """
    description: Description
    database: dict[pd.DataFrame]
    scenario: str = None  # The full scenario
    id: int = -1  # The id of the event

