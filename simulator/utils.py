from langchain import hub
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.runnables.base import Runnable
import importlib
import os
import sys
from langchain_core.prompts import ChatPromptTemplate

def get_prompt_template(args: dict) -> ChatPromptTemplate:
    if "prompt_hub_name" in args:
        hub_key = args.get("prompt_hub_key", None)
        return hub.pull(args["prompt_hub_name"], api_key=hub_key)
    elif "prompt" in args:
        return args["prompt"]
    elif 'from_str' in args:
        return ChatPromptTemplate.from_messages( [
                (
                    "system",
                    args['template'],
                )
            ])
    elif 'path' in args:
        with open(args['path'], 'r') as file:
            return ChatPromptTemplate.from_messages( [
                (
                    "system",
                    file.read(),
                )
            ])
    else:
        raise ValueError("Either prompt or prompt_hub_name should be provided")

def dict_to_str(d: dict, mode='items') -> str:
    final_str = ''
    for key, value in d.items():
        if mode == 'items':
            final_str+=f'- {key}: {value}\n'
        elif mode == 'rows':
            final_str+=f'# {key}: \n{value}\n----------------\n'
    return final_str

def set_llm_chain(llm: BaseChatModel, **kwargs) -> Runnable:
    """
    Initialize a chain
    """
    system_prompt_template = get_prompt_template(kwargs)
    if "structure" in kwargs:
        return system_prompt_template | llm.with_structured_output(kwargs["structure"])
    else:
        return system_prompt_template | llm

def load_tools(tools_path: str):
    """
    Load the agent tools from the function file
    """
    tools_dir = os.path.dirname(tools_path)
    if tools_dir not in sys.path:
        sys.path.insert(0, tools_dir)

    tools = []
    tools_schema = []
    try:
        spec = importlib.util.spec_from_file_location('agent_tools', tools_path)
        if spec is None:
            raise ImportError(f"Could not create ModuleSpec for {tools_path}")
        schema_parser = importlib.util.module_from_spec(spec)

        spec.loader.exec_module(schema_parser)
    except ImportError as e:
        raise ImportError(f"Error loading module {tools_path}: {e}")
    # <class 'langchain_core.tools.StructuredTool'>
    for attribute in dir(schema_parser):
        # Skip special attributes
        if not attribute.startswith("__"):
            value = getattr(schema_parser, attribute)
            attr_type = str(type(value))
            # This is hardcoded for now, should be careful when updating langchain version
            if "<class 'langchain_core.tools" in attr_type:
                tools.append(value)
                if hasattr(schema_parser, f'{attribute}_schema'):
                    tools_schema.append(getattr(schema_parser, f'{attribute}_schema'))
    return tools, tools_schema