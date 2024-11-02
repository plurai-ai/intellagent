# Copyright Sierra

import json
from typing import Any, Dict
from langchain.tools import StructuredTool

class ListAllAirports():
    @staticmethod
    def invoke(data: Dict[str, Any]) -> str:
        airports = [
            "SFO",
            "JFK",
            "LAX",
            "ORD",
            "DFW",
            "DEN",
            "SEA",
            "ATL",
            "MIA",
            "BOS",
            "PHX",
            "IAH",
            "LAS",
            "MCO",
            "EWR",
            "CLT",
            "MSP",
            "DTW",
            "PHL",
            "LGA",
        ]
        cities = [
            "San Francisco",
            "New York",
            "Los Angeles",
            "Chicago",
            "Dallas",
            "Denver",
            "Seattle",
            "Atlanta",
            "Miami",
            "Boston",
            "Phoenix",
            "Houston",
            "Las Vegas",
            "Orlando",
            "Newark",
            "Charlotte",
            "Minneapolis",
            "Detroit",
            "Philadelphia",
            "LaGuardia",
        ]
        return json.dumps({airport: city for airport, city in zip(airports, cities)})

    @staticmethod
    def get_info() -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "list_all_airports",
                "description": "List all airports and their cities.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            },
        }

list_all_airports_schema = ListAllAirports.get_info()
list_all_airports = StructuredTool.from_function(
        func=ListAllAirports.invoke,
        name=list_all_airports_schema['function']["name"],
        description=list_all_airports_schema['function']["description"],
    )