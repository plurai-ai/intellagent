# Copyright Sierra

from typing import Any, Dict
from langchain.tools import StructuredTool


class TransferToHumanAgents():
    @staticmethod
    def invoke(data: Dict[str, Any], summary: str) -> str:
        # This method simulates the transfer to a human agent.
        return "Transfer successful"

    @staticmethod
    def get_info() -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "transfer_to_human_agents",
                "description": (
                    "Transfer the user to a human agent, with a summary of the user's issue. "
                    "Only transfer if the user explicitly asks for a human agent, or if the user's issue cannot be resolved by the agent with the available tools."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "summary": {
                            "type": "string",
                            "description": "A summary of the user's issue.",
                        },
                    },
                    "required": ["summary"],
                },
            },
        }

transfer_to_human_agents_schema = TransferToHumanAgents.get_info()
transfer_to_human_agents = StructuredTool.from_function(
        func=TransferToHumanAgents.invoke,
        name=transfer_to_human_agents_schema['function']["name"],
        description=transfer_to_human_agents_schema['function']["description"],
    )