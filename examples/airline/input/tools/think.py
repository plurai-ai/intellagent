# Copyright Sierra

from typing import Any, Dict
from langchain.tools import StructuredTool

class Think():
    @staticmethod
    def invoke(data: Dict[str, Any], thought: str) -> str:
        return thought

    @staticmethod
    def get_info() -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "think",
                "description": "Use the tool to think about something. It will not obtain new information or change the database, but just append the thought to the log. Use it when complex reasoning is needed.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "thought": {
                            "type": "string",
                            "description": "A thought to think about.",
                        },
                    },
                    "required": ["thought"],
                },
            },
        }

think_schema = Think.get_info()
think = StructuredTool.from_function(
        func=Think.invoke,
        name=think_schema['function']["name"],
        description=think_schema['function']["description"],
    )