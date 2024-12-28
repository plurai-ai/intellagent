# Copyright Sierra
import json
from typing import Any, Dict
from langchain.tools import StructuredTool
from util import get_dict_json

class GetProductDetails():
    @staticmethod
    def invoke(data: Dict[str, Any], product_id: str) -> str:
        products = get_dict_json(data['products'], 'product_id')
        if product_id in products:
            return json.dumps(products[product_id])
        return "Error: product not found"

    @staticmethod
    def get_info() -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "get_product_details",
                "description": "Get the inventory details of a product.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "product_id": {
                            "type": "string",
                            "description": "The product id, such as '6086499569'. Be careful the product id is different from the item id.",
                        },
                    },
                    "required": ["product_id"],
                },
            },
        }

get_product_details_schema = GetProductDetails.get_info()
get_product_details = StructuredTool.from_function(
        func=GetProductDetails.invoke,
        name=get_product_details_schema['function']["name"],
        description=get_product_details_schema['function']["description"],
    )