# Copyright Sierra

from typing import Any, Dict
from langchain.tools import StructuredTool
import json
from util import get_dict_json, update_df


class CancelPendingOrder():
    @staticmethod
    def invoke(data: Dict[str, Any], order_id: str, reason: str) -> str:
        # check order exists and is pending
        orders = get_dict_json(data['orders'], 'order_id')
        users = get_dict_json(data['users'], 'user_id')
        if order_id not in orders:
            return "Error: order not found"
        order = orders[order_id]
        if order["status"].lower() != "pending":
            return "Error: non-pending order cannot be cancelled"

        # check reason
        if reason not in ["no longer needed", "ordered by mistake"]:
            return "Error: invalid reason"

        # handle refund
        refunds = []
        for payment in order["payment_history"]:
            payment_id = payment["payment_method_id"]
            refund = {
                "transaction_type": "refund",
                "amount": payment["amount"],
                "payment_method_id": payment_id,
            }
            refunds.append(refund)
            if "gift_card" in payment_id:  # refund to gift card immediately
                if payment_id not in users[order["user_id"]]["payment_methods"].keys():
                    users[order["user_id"]]["payment_methods"][payment_id] = {'source': 'gift_card',
                                                                              'brand': 'gift',
                                                                              'last_four': 4829,
                                                                              'id': payment_id,
                                                                              'balance': 30}
                payment_method = users[order["user_id"]]["payment_methods"][
                    payment_id
                ]
                if 'balance' not in payment_method.keys():
                    payment_method['balance'] = 30
                payment_method["balance"] += payment["amount"]
                payment_method["balance"] = round(payment_method["balance"], 2)

        # update order status
        order["status"] = "cancelled"
        order["cancel_reason"] = reason
        order["payment_history"].extend(refunds)
        update_df(data['orders'], order, 'order_id')
        update_df(data['users'], users[order["user_id"]], 'user_id')

        return json.dumps(order)

    @staticmethod
    def get_info() -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "cancel_pending_order",
                "description": (
                    "Cancel a pending order. If the order is already processed or delivered, "
                    "it cannot be cancelled. The agent needs to explain the cancellation detail "
                    "and ask for explicit user confirmation (yes/no) to proceed. If the user confirms, "
                    "the order status will be changed to 'cancelled' and the payment will be refunded. "
                    "The refund will be added to the user's gift card balance immediately if the payment "
                    "was made using a gift card, otherwise the refund would take 5-7 business days to process. "
                    "The function returns the order details after the cancellation."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "order_id": {
                            "type": "string",
                            "description": "The order id, such as '#W0000000'. Be careful there is a '#' symbol at the beginning of the order id.",
                        },
                        "reason": {
                            "type": "string",
                            "enum": ["no longer needed", "ordered by mistake"],
                            "description": "The reason for cancellation, which should be either 'no longer needed' or 'ordered by mistake'.",
                        },
                    },
                    "required": ["order_id", "reason"],
                },
            },
        }


cancel_pending_order_schema = CancelPendingOrder.get_info()
cancel_pending_order = StructuredTool.from_function(
    func=CancelPendingOrder.invoke,
    name=cancel_pending_order_schema['function']["name"],
    description=cancel_pending_order_schema['function']["description"],
)
