# Copyright Sierra
import json
from typing import Any, Dict
from langchain.tools import StructuredTool
from util import get_dict_json


class GetOrderDetails():
    @staticmethod
    def invoke(data: Dict[str, Any], order_id: str) -> str:
        orders = get_dict_json(data['orders'], 'order_id')
        if order_id in orders:
            return json.dumps(orders[order_id])
        return "Error: order not found"

    @staticmethod
    def get_info() -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "get_order_details",
                "description": "Get the status and details of an order.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "order_id": {
                            "type": "string",
                            "description": "The order id, such as '#W0000000'. Be careful there is a '#' symbol at the beginning of the order id.",
                        },
                    },
                    "required": ["order_id"],
                },
            },
        }

get_order_details_schema = GetOrderDetails.get_info()
get_order_details = StructuredTool.from_function(
        func=GetOrderDetails.invoke,
        name=get_order_details_schema['function']["name"],
        description=get_order_details_schema['function']["description"],
    )