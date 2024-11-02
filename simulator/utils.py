from langchain import hub
from langchain_core.language_models.llms import LLM
from langchain_core.runnables.base import Runnable

def dict_to_str(d: dict, mode='items') -> str:
    final_str = ''
    for key, value in d.items():
        if mode == 'items':
            final_str+=f'- {key}: {value}\n'
        elif mode == 'rows':
            final_str+=f'# {key}: \n{value}\n----------------\n'
    return final_str

def set_llm_chain(llm: LLM, **kwargs) -> Runnable:
    """
    Initialize a chain
    """
    if "prompt_hub_name" in kwargs:
        hub_key = kwargs.get("prompt_hub_key", None)
        system_prompt_template = hub.pull(kwargs["prompt_hub_name"], api_key=hub_key)
    elif "prompt" in kwargs:
        system_prompt_template = kwargs["prompt"]
    else:
        raise ValueError("Either prompt or prompt_hub_name should be provided")
    if "structure" in kwargs:
        return system_prompt_template | llm.with_structured_output(kwargs["template"])
    else:
        return system_prompt_template | llm