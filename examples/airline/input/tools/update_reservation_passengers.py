# Copyright Sierra

import json
from typing import Any, Dict, List
from langchain.tools import StructuredTool
from util import get_dict_json, update_df
class UpdateReservationPassengers():
    @staticmethod
    def invoke(
        data: Dict[str, Any],
        reservation_id: str,
        passengers: List[Dict[str, Any]],
    ) -> str:
        if 'reservations' not in data:
            return "Error: reservation not found, if you just created the resevation" \
                   " it might take a few minutes to be available."
        reservations = get_dict_json(data['reservations'], 'reservation_id')
        if reservation_id not in reservations:
            return "Error: reservation not found"
        reservation = reservations[reservation_id]
        if len(passengers) != len(reservation["passengers"]):
            return "Error: number of passengers does not match"
        reservation['passengers'] = passengers
        update_df(data['reservations'], reservation, 'reservation_id')
        return json.dumps(reservation)

    @staticmethod
    def get_info() -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "update_reservation_passengers",
                "description": "Update the passenger information of a reservation.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "reservation_id": {
                            "type": "string",
                            "description": "The reservation ID, such as 'ZFA04Y'.",
                        },
                        "passengers": {
                            "type": "array",
                            "description": "An array of objects containing details about each passenger.",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "first_name": {
                                        "type": "string",
                                        "description": "The first name of the passenger, such as 'Noah'.",
                                    },
                                    "last_name": {
                                        "type": "string",
                                        "description": "The last name of the passenger, such as 'Brown'.",
                                    },
                                    "dob": {
                                        "type": "string",
                                        "description": "The date of birth of the passenger in the format 'YYYY-MM-DD', such as '1990-01-01'.",
                                    },
                                },
                                "required": ["first_name", "last_name", "dob"],
                            },
                        },
                    },
                    "required": ["reservation_id", "passengers"],
                },
            },
        }

update_reservation_passengers_schema = UpdateReservationPassengers.get_info()
update_reservation_passengers = StructuredTool.from_function(
        func=UpdateReservationPassengers.invoke,
        name=update_reservation_passengers_schema['function']["name"],
        description=update_reservation_passengers_schema['function']["description"],
    )