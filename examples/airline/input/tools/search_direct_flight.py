# Copyright Sierra

import json
from typing import Any, Dict
from langchain.tools import StructuredTool
from util import get_dict_json, update_df
class SearchDirectFlight():
    @staticmethod
    def invoke(data: Dict[str, Any], origin: str, destination: str, date: str) -> str:
        flights = get_dict_json(data['flights'], 'flight_number')
        results = []
        results_backup = []
        backup_flights = []
        for flight in flights.values():
            if flight["origin"] == origin and flight["destination"] == destination:
                if date not in flight['dates']:
                    flight['dates'][date] = {'status': 'available', 'available_seats': {'basic_economy': 20, 'economy': 15, 'business': 10}, 'prices': {'basic_economy': 99, 'economy': 150, 'business': 500}}
                    results_backup.append({k: v for k, v in flight.items() if k != "dates"})
                    results_backup[-1].update(flight['dates'][date])
                    backup_flights.append(flight)
                elif flight['dates'][date]['status'] == 'available':
                    results.append({k: v for k, v in flight.items() if k != "dates"})
                    results[-1].update(flight['dates'][date])
        if not results:
            for flight in backup_flights:
                update_df(data['flights'], flight, 'flight_number')
            return json.dumps(results_backup)
        return json.dumps(results)

    @staticmethod
    def get_info() -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "search_direct_flight",
                "description": "Search direct flights between two cities on a specific date.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "origin": {
                            "type": "string",
                            "description": "The origin city airport in three letters, such as 'JFK'.",
                        },
                        "destination": {
                            "type": "string",
                            "description": "The destination city airport in three letters, such as 'LAX'.",
                        },
                        "date": {
                            "type": "string",
                            "description": "The date of the flight in the format 'YYYY-MM-DD', such as '2024-01-01'.",
                        },
                    },
                    "required": ["origin", "destination", "date"],
                },
            },
        }

search_direct_flight_schema = SearchDirectFlight.get_info()
search_direct_flight = StructuredTool.from_function(
        func=SearchDirectFlight.invoke,
        name=search_direct_flight_schema['function']["name"],
        description=search_direct_flight_schema['function']["description"],
    )