# Copyright Sierra
from langchain.tools import StructuredTool
import json
from typing import Any, Dict
from util import get_dict_json


class GetReservationDetails():
    @staticmethod
    def invoke(data: Dict[str, Any], reservation_id: str) -> str:
        if 'reservations' not in data:
            return "Error: reservation not found, if you just created the resevation" \
                   " it might take a few minutes to be available."
        reservations = get_dict_json(data['reservations'], 'reservation_id')
        if reservation_id in reservations:
            return json.dumps(reservations[reservation_id])
        return "Error: reservation not found, if you just created the reservation" \
               " it might take a few minutes to be available."

    @staticmethod
    def get_info() -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "get_reservation_details",
                "description": "Get the details of a reservation.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "reservation_id": {
                            "type": "string",
                            "description": "The reservation id, such as '8JX2WO'.",
                        },
                    },
                    "required": ["reservation_id"],
                },
            },
        }

get_reservation_details_schema = GetReservationDetails.get_info()
get_reservation_details = StructuredTool.from_function(
        func=GetReservationDetails.invoke,
        name=get_reservation_details_schema['function']["name"],
        description=get_reservation_details_schema['function']["description"],
    )
