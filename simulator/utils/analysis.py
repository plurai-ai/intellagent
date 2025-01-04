from simulator.utils.parallelism import async_batch_invoke
from simulator.utils.llm_utils import get_llm, set_llm_chain, set_callback
from pydantic import BaseModel, Field
from typing import List
from simulator.dataset.events_generator import Event
from simulator.dataset.descriptor_generator import policies_list_to_str
from simulator.utils.llm_utils import convert_messages_to_str
from typing import Optional


class PoliciesAnalysis(BaseModel):
    conversation_policies: List[int] = Field(
        description="The sublist of the **indexes** of all the policies that are relevant to the conversation")
    violated_policies: Optional[List[int]] = Field(
        default=[],  # Explicitly set a default value
        description="The sublist of the **indexes** of all the policies that are violated in the conversation, if non return an empty list")


def policy_to_str(policy):
    return f"Flow: {policy['flow']}\npolicy: {policy['policy']}"


def get_dialog_policies(config: dict, simulator_res: list[dict], events: list[Event]) -> list[dict]:
    """
    Get the dialog policies from the config
    :param config: The config analysis chain
    :param simulator_res: The results of the simulator
    :param events: The events list
    :return: enriching the simulator_res with the policies information
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
                      'judgment': f"{r['res']['stop_signal']}\n{judgment_reason}",
                      'feedback': r['res']['critique_feedback']})

    num_workers = config.get('num_workers', 1)
    timeout = config.get('timeout', 10)
    res = async_batch_invoke(llm.ainvoke, batch, num_workers=num_workers, timeout=timeout, callbacks=[callback])
    for r in res:
        if r['error'] is not None:
            continue
        cur_event = events[simulator_res[r['index']]['event_id'] - 1]
        cur_policies = cur_event.description.policies
        simulator_res[r['index']]['tested_challenge_level'] = sum([cur_policies[l]['score'] for
                                                                   l in r['result'].conversation_policies
                                                                   if l < len(cur_policies)])
        simulator_res[r['index']]['tested_policies'] = r['result'].conversation_policies
        simulator_res[r['index']]['violated_policies'] = r['result'].violated_policies
    return simulator_res
