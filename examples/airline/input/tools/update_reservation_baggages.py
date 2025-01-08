# Copyright Sierra

import json
from typing import Any, Dict
from langchain.tools import StructuredTool
from util import get_dict_json, update_df
class UpdateReservationBaggages():
    @staticmethod
    def invoke(
            data: Dict[str, Any],
            reservation_id: str,
            total_baggages: int,
            nonfree_baggages: int,
            payment_id: str,
    ) -> str:
        if 'reservations' not in data:
            return "Error: reservation not found, if you just created the reservation" \
                   " it might take a few minutes to be available."
        reservations = get_dict_json(data['reservations'], 'reservation_id')
        users = get_dict_json(data['users'], 'user_id')
        if reservation_id not in reservations:
            return "Error: reservation not found"
        reservation = reservations[reservation_id]

        total_price = 50 * max(0, nonfree_baggages - reservation["nonfree_baggages"])
        if payment_id not in users[reservation["user_id"]]["payment_methods"]:
            return "Error: payment method not found"
        payment_method = users[reservation["user_id"]]["payment_methods"][payment_id]
        if payment_method["source"] == "certificate":
            return "Error: certificate cannot be used to update reservation"
        elif (
                payment_method["source"] == "gift_card"
                and payment_method["amount"] < total_price
        ):
            return "Error: gift card balance is not enough"

        reservation["total_baggages"] = total_baggages
        reservation["nonfree_baggages"] = nonfree_baggages
        if payment_method["source"] == "gift_card":
            payment_method["amount"] -= total_price

        if total_price != 0:
            reservation["payment_history"].append(
                {
                    "payment_id": payment_id,
                    "amount": total_price,
                }
            )
        update_df(data['reservations'], reservation, 'reservation_id')
        return json.dumps(reservation)

    @staticmethod
    def get_info() -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "update_reservation_baggages",
                "description": "Update the baggage information of a reservation.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "reservation_id": {
                            "type": "string",
                            "description": "The reservation ID, such as 'ZFA04Y'.",
                        },
                        "total_baggages": {
                            "type": "integer",
                            "description": "The updated total number of baggage items included in the reservation.",
                        },
                        "nonfree_baggages": {
                            "type": "integer",
                            "description": "The updated number of non-free baggage items included in the reservation.",
                        },
                        "payment_id": {
                            "type": "string",
                            "description": "The payment id stored in user profile, such as 'credit_card_7815826', 'gift_card_7815826', 'certificate_7815826'.",
                        },
                    },
                    "required": [
                        "reservation_id",
                        "total_baggages",
                        "nonfree_baggages",
                        "payment_id",
                    ],
                },
            },
        }


update_reservation_baggage_schema = UpdateReservationBaggages.get_info()
update_reservation_baggage = StructuredTool.from_function(
    func=UpdateReservationBaggages.invoke,
    name=update_reservation_baggage_schema['function']["name"],
    description=update_reservation_baggage_schema['function']["description"],
)
