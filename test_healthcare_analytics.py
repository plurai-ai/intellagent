import os
from simulator.healthcare_analytics import (
    get_user_id,
    do_not_track,
    _usage_event_debugging,
    BaseEvent,
    ExtractFlowEvent,
    FlowToPoliciesEvent,
    GenerateRelationsGraphEvent,
    RunSimulationEvent,
    FailureEvent,
    track_event,
    silent,
    track_event_was_completed
)

@silent
def test_get_user_id():
    """Test user ID generation and retrieval."""
    user_id = get_user_id()
    print(f"User ID: {user_id}")
    assert isinstance(user_id, str) and user_id.startswith("u-"), "User ID should start with 'u-' and be a string."
    assert len(user_id) > 2, "User ID should not be empty."

@silent
def test_do_not_track():
    """Test tracking toggle."""
    os.environ["PLURAI_DO_NOT_TRACK"] = "true"
    assert do_not_track() is True, "do_not_track() should return True when PLURAI_DO_NOT_TRACK is 'true'."
    os.environ["PLURAI_DO_NOT_TRACK"] = "false"
    assert do_not_track() is False, "do_not_track() should return False when PLURAI_DO_NOT_TRACK is 'false'."

@silent
def test_usage_event_debugging():
    """Test usage event debugging toggle."""
    os.environ["PLURAI_DEBUG_TRACKING"] = "true"
    assert _usage_event_debugging() is True, "_usage_event_debugging() should return True when PLURAI_DEBUG_TRACKING is 'true'."
    os.environ["PLURAI_DEBUG_TRACKING"] = "false"
    assert _usage_event_debugging() is False, "_usage_event_debugging() should return False when PLURAI_DEBUG_TRACKING is 'false'."

@silent
def test_extract_flow_event():
    """Test tracking an extract flow event."""
    event = ExtractFlowEvent(
        event_type="extract_flow",
        run_id="test-run-001",
        status="success",
        n_flows=5
    )
    result = track_event(event)
    print(f"Extract Flow Event Tracked: {event}")
    assert result is not None, "Event tracking should not return None."

@silent
def test_flow_to_policies_event():
    """Test tracking a flow-to-policies event."""
    event = FlowToPoliciesEvent(
        event_type="flow_to_policies",
        run_id="test-run-002",
        status="success",
        n_policies_per_flow=[3, 5, 2]
    )
    result = track_event(event)
    print(f"Flow to Policies Event Tracked: {event}")
    assert result is not None, "Event tracking should not return None."

@silent
def test_generate_relations_graph_event():
    """Test tracking a generate relations graph event."""
    event = GenerateRelationsGraphEvent(
        event_type="generate_relations_graph",
        run_id="test-run-003",
        status="success",
        n_edges=10,
        avg_rank=2.5
    )
    result = track_event(event)
    print(f"Generate Relations Graph Event Tracked: {event}")
    assert result is not None, "Event tracking should not return None."

@silent
def test_run_simulation_event():
    """Test tracking a run simulation event."""
    event = RunSimulationEvent(
        event_type="run_simulation",
        run_id="test-run-004",
        status="success",
        n_dialogs=50
    )
    result = track_event(event)
    print(f"Run Simulation Event Tracked: {event}")
    assert result is not None, "Event tracking should not return None."

@silent
def test_failure_event():
    """Test tracking a failure event."""
    event = FailureEvent(
        event_type="failure",
        run_id="test-run-005",
        error_message="Simulated error",
        exception_type="TestException",
        status="failure"
    )
    result = track_event(event)
    print(f"Failure Event Tracked: {event}")
    assert result is not None, "Event tracking should not return None."

@track_event_was_completed
def example_function():
    """Example function to demonstrate track_event_was_completed."""
    print("Executing example function...")
    return "Function Completed"

@silent
def test_track_event_was_completed():
    """Test track_event_was_completed decorator."""
    result = example_function()
    print(f"Track Event Was Completed Result: {result}")
    assert result == "Function Completed", "Decorated function should return 'Function Completed'."

def main():
    os.environ["PLURAI_DO_NOT_TRACK"] = "false"
    print("Starting Tests...")
    print("\nTesting get_user_id...")
    test_get_user_id()

    print("\nTesting do_not_track...")
    test_do_not_track()

    print("\nTesting _usage_event_debugging...")
    test_usage_event_debugging()

    print("\nTesting ExtractFlowEvent...")
    test_extract_flow_event()

    print("\nTesting FlowToPoliciesEvent...")
    test_flow_to_policies_event()

    print("\nTesting GenerateRelationsGraphEvent...")
    test_generate_relations_graph_event()

    print("\nTesting RunSimulationEvent...")
    test_run_simulation_event()

    print("\nTesting FailureEvent...")
    test_failure_event()

    print("\nTesting track_event_was_completed decorator...")
    test_track_event_was_completed()

    print("\nAll tests completed successfully.")

if __name__ == "__main__":
    main()
