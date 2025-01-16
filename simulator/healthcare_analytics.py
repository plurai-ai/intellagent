import os
import json
import uuid
import logging
import requests
from datetime import datetime
from functools import wraps, lru_cache
from pydantic import BaseModel, Field
from typing import Optional


# Configuration
USAGE_TRACKING_URL = "https://simulator-analytics.azurewebsites.net/api/index_event"
USER_DATA_DIR_NAME = "plurai_analytics"
DO_NOT_TRACK_ENV = "PLURAI_DO_NOT_TRACK"
DEBUG_TRACKING_ENV = "PLURAI_DEBUG_TRACKING"
TRACK_TIMEOUT = 1  # seconds

# Logger setup
logger = logging.getLogger(__name__)
# Do not configure logging.basicConfig in libraries
logger.addHandler(logging.NullHandler())

# Utility: Get or generate user ID
def get_unique_id() -> str:
    user_data_path = os.path.expanduser(f"~/.{USER_DATA_DIR_NAME}")
    user_id_file = os.path.join(user_data_path, "unique_id.json")
    try:
        if os.path.exists(user_id_file):
            with open(user_id_file, "r") as f:
                user_id = json.load(f).get("unique_id")
                if user_id:
                    return user_id
        # Generate new unique_id
        user_id = f"u-{uuid.uuid4().hex}"
        os.makedirs(user_data_path, exist_ok=True)
        with open(user_id_file, "w") as f:
            json.dump({"unique_id": user_id}, f)
        return user_id
    except Exception as e:
        logger.error(f"Failed to get or create user_id: {e}")
        # Return a new user_id without persisting it
        return f"u-{uuid.uuid4().hex}"

@lru_cache(maxsize=None)
def do_not_track() -> bool:
    """
    Returns True if and only if the environment variable is defined and has value "true".
    The result is cached for better performance.
    """
    return os.environ.get(DO_NOT_TRACK_ENV, "false").lower() == "true"

@lru_cache(maxsize=None)
def _usage_event_debugging() -> bool:
    """
    For developers: Debug and print event payload if turned on.
    The result is cached for better performance.
    """
    return os.environ.get(DEBUG_TRACKING_ENV, "false").lower() == "true"

# Base Event Class
class BaseEvent(BaseModel):
    unique_id: str = Field(default_factory=get_unique_id)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    event_type: str = Field(default=None, init=False)  # Automatically set
    cost: Optional[float] = Field(default=0)
    error_message: Optional[str] = Field(default=None)
    
    def __init__(self, **data):
        super().__init__(**data)
        self.event_type = self.__class__.__name__  # Set event_type to class name

class ExtractFlowEvent(BaseEvent):
    n_flows: int
    prompt_length: int
    llm_policy: dict

class ExtractFlowPoliciesEvent(BaseEvent):
    n_policies_per_flow: list[int]
    llm_policy: dict
    
class GenerateRelationsGraphEvent(BaseEvent):
    n_edges: int
    avg_edge_weight: float
    std_edge_weight : float
    llm_edge: dict

class GenerateDatasetEvent(BaseEvent):
    initial_n_samples: int
    total_n_samples: int
    initial_n_iterations: int
    total_n_iterations : int
    avg_challenge_score: float
    std_challenge_score: float
    avg_n_policies: float
    llm_description_generator: dict
    llm_description_refinement: dict
    llm_event_graph_generator: dict
    
class RunSimulationEvent(BaseEvent):
    n_dialogs: int
    avg_n_user_messages_per_dialog: float
    avg_n_chatbot_messages_per_dialog: float
    llm_critique: dict
    llm_user: dict
    llm_chat: dict 
    
class AnalyzeSimulationResultsEvent(BaseEvent):
    failure_rate : float

class ExceptionEvent(BaseEvent):
    error_message: str
    exception_type: str

# Silent Decorator
def silent(func):
    """Decorator to silence errors in tracking."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Tracking failed: {e}")
            return None
    return wrapper

# Send Event Function
@silent
def track_event(event: BaseEvent):
    if do_not_track():
        logger.info("Tracking is disabled.")
        return
    
    # Convert the event to a dictionary and serialize datetime to ISO 8601 format
    payload = event.dict()
    payload["timestamp"] = payload["timestamp"].isoformat()

    if _usage_event_debugging():
        logger.debug(f"Debugging Event Payload: {payload}")
        return True
    
    try:
        response = requests.post(USAGE_TRACKING_URL, json=payload, timeout=TRACK_TIMEOUT)
        response.raise_for_status()
        logger.info(f"Event sent successfully: {payload}")
        return True
    except requests.Timeout as e:
        logger.error(f"Request timed out: {e}")
        return False
    except requests.HTTPError as e:
        logger.error(f"HTTP error occurred: {e.response.status_code} - {e.response.text}")
        return False
    except requests.RequestException as e:
        logger.error(f"Request failed: {e}")
        return False
'''
if __name__ == "__main__":
    # Create a test event
    test_event = GenerateDatasetEvent(
        event_type="TestEvent",
        initial_n_samples=100,
        total_n_samples=500,
        initial_n_iterations=5,
        total_n_iterations=20,
        avg_challenge_score=0.8,
        std_challenge_score=0.05,
        avg_n_policies=3.5
    )

    # Call the track_event function
    success = track_event(test_event)
    if success:
        print("Test event tracked successfully!")
    else:
        print("Failed to track the test event.")    
'''
