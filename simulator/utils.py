from langchain import hub
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.runnables.base import Runnable
import importlib
import os
import sys
import logging
from typing import Any
from langchain_community.callbacks import get_openai_callback
from langchain_community.callbacks.manager import get_bedrock_anthropic_callback
from langchain_core.callbacks import BaseCallbackHandler
from langchain_openai import ChatOpenAI
from langchain.llms.huggingface_pipeline import HuggingFacePipeline
from langchain_openai.chat_models import AzureChatOpenAI
import contextlib
from langchain_core.prompts import ChatPromptTemplate
from tqdm import trange, tqdm
import concurrent.futures
import yaml
from pathlib import Path


LLM_ENV = yaml.safe_load(open('config/llm_env.yml', 'r'))

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
                    args['from_str']['template'],
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

def get_latest_file(directory_path,extension = 'json') -> Path:
    """
    Get the most recently modified file in a directory with a specific extension
    :param directory_path:
    :param extension:
    :return: The most recently modified file
    """
    # Convert the directory path to a Path object
    directory_path = Path(directory_path)

    # Get a list of all JSON files in the directory
    json_files = [f for f in directory_path.glob(f"*.{extension}") if f.is_file()]

    # Find the most recently modified JSON file
    latest_json_file = max(json_files, key=lambda f: f.stat().st_mtime, default=None)

    return latest_json_file
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

def append_line_to_file(file_path, text):
    with open(file_path, 'a') as file:  # 'a' mode opens the file for appending
        file.write(text + '\n')


class DummyCallback:
    """
    A dummy callback for the LLM.
    This is a trick to handle an empty callback.
    """

    def __enter__(self):
        self.total_cost = 0
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        pass
def get_dummy_callback():
    return DummyCallback()

def set_callbck(llm_type):
    if llm_type.lower() == 'openai' or llm_type.lower() == 'azure':
        callback = get_openai_callback
    elif llm_type.lower() == 'anthropic_bedrock':
        callback = get_bedrock_anthropic_callback
    else:
        callback = get_dummy_callback
    return callback

def get_llm(config: dict):
    """
    Returns the LLM model
    :param config: dictionary with the configuration
    :return: The llm model
    """
    if 'temperature' not in config:
        temperature = 0
    else:
        temperature = config['temperature']
    if 'model_kwargs' in config:
        model_kwargs = config['model_kwargs']
    else:
        model_kwargs = {}

    if config['type'].lower() == 'openai':
        if LLM_ENV['openai']['OPENAI_ORGANIZATION'] == '':
            return ChatOpenAI(temperature=temperature, model_name=config['name'],
                              openai_api_key=config.get('openai_api_key', LLM_ENV['openai']['OPENAI_API_KEY']),
                              openai_api_base=config.get('openai_api_base', 'https://api.openai.com/v1'),
                              model_kwargs=model_kwargs)
        else:
            return ChatOpenAI(temperature=temperature, model_name=config['name'],
                              openai_api_key=config.get('openai_api_key', LLM_ENV['openai']['OPENAI_API_KEY']),
                              openai_api_base=config.get('openai_api_base', 'https://api.openai.com/v1'),
                              openai_organization=config.get('openai_organization', LLM_ENV['openai']['OPENAI_ORGANIZATION']),
                              model_kwargs=model_kwargs)
    elif config['type'].lower() == 'azure':
        return AzureChatOpenAI(temperature=temperature, azure_deployment=config['name'],
                        openai_api_key=config.get('openai_api_key', LLM_ENV['azure']['AZURE_OPENAI_API_KEY']),
                        azure_endpoint=config.get('azure_endpoint', LLM_ENV['azure']['AZURE_OPENAI_ENDPOINT']),
                        openai_api_version=config.get('openai_api_version', LLM_ENV['azure']['OPENAI_API_VERSION']))

    elif config['type'].lower() == 'google':
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(temperature=temperature, model=config['name'],
                              google_api_key=LLM_ENV['google']['GOOGLE_API_KEY'],
                              model_kwargs=model_kwargs)


    elif config['type'].lower() == 'huggingfacepipeline':
        device = config.get('gpu_device', -1)
        device_map = config.get('device_map', None)

        return HuggingFacePipeline.from_model_id(
            model_id=config['name'],
            task="text-generation",
            pipeline_kwargs={"max_new_tokens": config['max_new_tokens']},
            device=device,
            device_map=device_map
        )
    else:
        raise NotImplementedError("LLM not implemented")