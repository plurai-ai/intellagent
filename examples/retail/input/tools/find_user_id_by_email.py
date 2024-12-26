# Copyright Sierra

from typing import Any, Dict
from langchain.tools import StructuredTool


class FindUserIdByEmail():
    @staticmethod
    def invoke(data: Dict[str, Any], email: str) -> str:
        users = data["users"].set_index('user_id', drop=False).to_dict(orient='index')
        for user_id, profile in users.items():
            if profile["email"].lower() == email.lower():
                return user_id
        return "Error: user not found"

    @staticmethod
    def get_info() -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "find_user_id_by_email",
                "description": "Find user id by email. If the user is not found, the function will return an error message.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "email": {
                            "type": "string",
                            "description": "The email of the user, such as 'something@example.com'.",
                        },
                    },
                    "required": ["email"],
                },
            },
        }

find_user_id_by_email_schema = FindUserIdByEmail.get_info()
find_user_id_by_email = StructuredTool.from_function(
        func=FindUserIdByEmail.invoke,
        name=find_user_id_by_email_schema['function']["name"],
        description=find_user_id_by_email_schema['function']["description"],
    )