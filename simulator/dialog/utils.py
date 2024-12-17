import re
from simulator.agents_graphs.dialog_graph import DialogState


def contains_isolated_correct(text):
    """
    Check if the word 'CORRECT' exists in the text, surrounded only by non-letters or nothing.

    Args:
        text (str): The input string.

    Returns:
        bool: True if 'CORRECT' is found isolated, False otherwise.
    """
    pattern = r'(?<![a-zA-Z])CORRECT(?![a-zA-Z])'
    return bool(re.search(pattern, text))


def intermediate_processing(state: DialogState):
    """Process the state of the dialog and determine what is the next step."""
    if state['stop_signal'] == '':  # Else, there is a stop signal from the user
        return 'chatbot'
    # Check if there is a feedback from the critique
    if state['critique_feedback'] == '':
        return 'end_critique'
    # Check if the user behavior is correct
    if contains_isolated_correct(state['critique_feedback']):
        return 'END'
    else:
        return 'user'
