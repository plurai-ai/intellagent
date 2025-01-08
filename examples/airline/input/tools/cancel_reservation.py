# Copyright Sierra

import json
from typing import Any, Dict
from langchain.tools import StructuredTool
from util import get_dict_json, update_df
class CancelReservation():
    @staticmethod
    def invoke(
        data: Dict[str, Any],
        reservation_id: str,
    ) -> str:
        if 'reservations' not in data:
            return "Error: reservation not found, if you just created the reservation it might take a few minutes to be available."
        reservations = get_dict_json(data['reservations'], 'reservation_id')
        if reservation_id not in reservations:
            return "Error: reservation not found"
        reservation = reservations[reservation_id]

        # reverse the payment
        refunds = []
        for payment in reservation["payment_history"]:
            refunds.append(
                {
                    "payment_id": payment["payment_id"],
                    "amount": -payment["amount"],
                }
            )
        reservation["payment_history"].extend(refunds)
        reservation["status"] = "cancelled"
        update_df(data['reservations'], reservation, 'reservation_id')
        return json.dumps(reservation)

    @staticmethod
    def get_info() -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "cancel_reservation",
                "description": "Cancel the whole reservation.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "reservation_id": {
                            "type": "string",
                            "description": "The reservation ID, such as 'ZFA04Y'.",
                        },
                    },
                    "required": ["reservation_id"],
                },
            },
        }

cancel_reservation_schema = CancelReservation.get_info()
cancel_reservation = StructuredTool.from_function(
        func=CancelReservation.invoke,
        name=cancel_reservation_schema['function']["name"],
        description=cancel_reservation_schema['function']["description"],
    )