# Copyright Sierra
import json
from typing import Any, Dict
from langchain.tools import StructuredTool


class GetUserDetails():
    @staticmethod
    def invoke(data: Dict[str, Any], user_id: str) -> str:
        users = data["users"].set_index('user_id', drop=False).to_dict(orient='index')
        if user_id in users:
            return json.dumps(users[user_id])
        return "Error: user not found"

    @staticmethod
    def get_info() -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "get_user_details",
                "description": "Get the details of a user.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "user_id": {
                            "type": "string",
                            "description": "The user id, such as 'sara_doe_496'.",
                        },
                    },
                    "required": ["user_id"],
                },
            },
        }

get_user_details_schema = GetUserDetails.get_info()
get_user_details = StructuredTool.from_function(
        func=GetUserDetails.invoke,
        name=get_user_details_schema['function']["name"],
        description=get_user_details_schema['function']["description"],
    )