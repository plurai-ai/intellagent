from simulator.utils.parallelism import async_batch_invoke
from simulator.utils.llm_utils import get_llm, set_llm_chain, set_callback
from pydantic import BaseModel, Field
from typing import List
from simulator.dataset.events_generator import Event
from simulator.dataset.descriptor_generator import policies_list_to_str
from simulator.utils.llm_utils import convert_messages_to_str

class PoliciesAnalysis(BaseModel):
    conversation_policies: List[int] = Field(
        description="The sublist of the **indexes** of all the policies that are relevant to the conversation")
    violated_policies: List[int] = Field(
        description="The sublist of the **indexes** of all the policies that are violated in the conversation, if non return an empty list")


def policy_to_str(policy):
    return f"Flow: {policy['flow']}\npolicy: {policy['policy']}"

def get_dialog_policies(config: dict, simulator_res: list[dict], events: list[Event]) -> list[dict]:
    """
    Get the dialog policies from the config
    :param config: The config analysis chain
    :param simulator_res: The results of the simulator
    :param events: The events list
    :return: The dialog policies
    """

    llm = get_llm(config['llm'])
    llm = set_llm_chain(llm, **config['prompt'], structure=PoliciesAnalysis)
    batch = []
    callback = set_callback(config['llm']['type'])
    for r in simulator_res:
        cur_event = events[r['event_id'] - 1]
        judgment_reason = r['res']['user_thoughts'][-1].split('Thought:\n')[-1]
        batch.append({'policies': policies_list_to_str(cur_event.description.policies),
                      'conversation': convert_messages_to_str(r['res']['chatbot_messages'][1:]),
                      'judgment':  f"{r['res']['stop_signal']}\n{judgment_reason}",
                      'feedback':  r['res']['critique_feedback']})

    num_workers = config.get('num_workers', 1)
    timeout = config.get('timeout', 10)
    res = async_batch_invoke(llm.ainvoke, batch, num_workers=num_workers, timeout=timeout, callbacks=[callback])
    return res