from langchain import hub
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.runnables.base import Runnable
import importlib
import os
import sys
from langchain_community.callbacks import get_openai_callback
from langchain_community.callbacks.manager import get_bedrock_anthropic_callback
from langchain_openai import ChatOpenAI
from langchain_community.llms import HuggingFacePipeline
from langchain_openai.chat_models import AzureChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
import yaml
from simulator.healthcare_analytics import ExceptionEvent, track_event
from langchain_core.messages import HumanMessage, AIMessage
import pandas as pd

LLM_ENV = yaml.safe_load(open('config/llm_env.yml', 'r'))


def get_prompt_template(args: dict) -> ChatPromptTemplate:
    if "prompt_hub_name" in args:
        hub_key = args.get("prompt_hub_key", None)
        return hub.pull(args["prompt_hub_name"], api_key=hub_key)
    elif "prompt" in args:
        return args["prompt"]
    elif 'from_str' in args:
        return ChatPromptTemplate.from_messages([
            (
                "system",
                args['from_str']['template'],
            )
        ])
    elif 'path' in args:
        with open(args['path'], 'r') as file:
            return ChatPromptTemplate.from_messages([
                (
                    "system",
                    file.read(),
                )
            ])
    else:
        raise ValueError("Either prompt or prompt_hub_name should be provided")


def convert_messages_to_str(messages: list, with_tools=False) -> str:
    """
    Convert a list of (langchain) messages to a string
    """
    formatted_string = ''
    for msg in messages:
        if msg.type == 'system':
            continue
        if hasattr(msg, 'tool_calls'):
            if with_tools:
                for tool_call in msg.tool_calls:
                    formatted_string += f"chatbot calling function: {tool_call['name']}, with args: {str(tool_call['args'])}\n"
            if msg.content == '':
                continue
        if msg.type == 'tool':
            if with_tools:
                formatted_string += f"chatbot tool_response: {msg.content}\n"
            continue

        if isinstance(msg.content, list):
            if (not msg.content) or ('text' not in msg.content[0].keys()):
                continue
            msg_content = msg.content[0]['text']
        else:
            msg_content = msg.content
        msg_content = msg_content.rstrip('\n')

        formatted_string += f"{'user' if isinstance(msg, HumanMessage) else 'chatbot'}: {msg_content}\n"
    return formatted_string


def dict_to_str(d: dict, mode='items') -> str:
    final_str = ''
    for key, value in d.items():
        if mode == 'items':
            final_str += f'- {key}: {value}\n'
        elif mode == 'rows':
            final_str += f'# {key}: \n{value}\n----------------\n'
    return final_str


def data_to_str(data: dict[pd.DataFrame]):
    return '\n'.join([f"## Table: {name}\n ### Table information:\n{df.to_json(orient='records', lines=True)}" for
                      name, df in data.items()])


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
    if not os.path.isfile(tools_path):
        return [], []
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
        error_message = f"Error loading module {tools_path}: {e}"
        track_event(ExceptionEvent(exception_type=type(e).__name__,
                                   error_message=error_message))
        raise ImportError(error_message)
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


def convert_to_anthropic_tools(
        tools_schema: list[dict],
) -> list[dict]:
    """Convert an openAI tools schema to anthropic"""
    # already in Anthropic tool format
    result_schema = []
    for tool in tools_schema:
        if isinstance(tool, dict) and all(
                k in tool for k in ("name", "description", "input_schema")
        ):
            result_schema.append(tool)
        else:
            if 'function' not in tool.keys():
                raise ValueError("not valid openAI schema")
            oai_formatted = tool["function"]
            if not all(k in oai_formatted for k in ("name", "description", "parameters")):
                raise ValueError("not valid openAI schema")
            result_schema.append({'name': oai_formatted["name"],
                                  'description': oai_formatted['description'],
                                  'input_schema': oai_formatted["parameters"]})
    return result_schema

def convert_to_oci_schema(tools_schema: list[dict]) -> list[dict]:
    res_schema = []
    for tool in tools_schema:
        tool = tool['function']
        parameters = {}
        for i, p in tool['parameters']['properties'].items():
            parameters[i] = p
            if i not in tool['parameters']['required']:
                parameters[i]['default'] = ''
            parameters[i]['is_required'] = i in tool['parameters']['required']
        res_schema.append({'title': tool['name'], 'description': tool['description'], 'properties': parameters})
    return res_schema




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


def set_callback(llm_type):
    if llm_type.lower() == 'openai' or llm_type.lower() == 'azure':
        callback = get_openai_callback
    elif llm_type.lower() == 'anthropic_bedrock':
        callback = get_bedrock_anthropic_callback
    else:
        callback = get_dummy_callback
    return callback


def load_yaml_content(yaml_content: str) -> dict:
    """
    Load YAML content into a Python dictionary, handling YAML blocks with ```yml prefixes.

    Args:
        yaml_content (str): The YAML content as a string, potentially wrapped with ```yml and ``` markers.

    Returns:
        dict: The parsed YAML content as a dictionary.
    """
    try:
        index = yaml_content.find('```yml')
        yaml_content = yaml_content[index:] if index != -1 else yaml_content
        # Remove ```yml and ``` markers if they exist
        if yaml_content.startswith("```yml"):
            yaml_content = yaml_content.strip("```yml").strip("```").strip()

        # Load the YAML content
        return yaml.safe_load(yaml_content)
    except yaml.YAMLError as e:
        return {}


def get_llm(config: dict, timeout=60):
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
                              model_kwargs=model_kwargs, timeout=timeout)
        else:
            return ChatOpenAI(temperature=temperature, model_name=config['name'],
                              openai_api_key=config.get('openai_api_key', LLM_ENV['openai']['OPENAI_API_KEY']),
                              openai_api_base=config.get('openai_api_base', 'https://api.openai.com/v1'),
                              openai_organization=config.get('openai_organization',
                                                             LLM_ENV['openai']['OPENAI_ORGANIZATION']),
                              model_kwargs=model_kwargs, timeout=timeout)
    elif config['type'].lower() == 'azure':
        return AzureChatOpenAI(temperature=temperature, azure_deployment=config['name'],
                               openai_api_key=config.get('openai_api_key', LLM_ENV['azure']['AZURE_OPENAI_API_KEY']),
                               azure_endpoint=config.get('azure_endpoint', LLM_ENV['azure']['AZURE_OPENAI_ENDPOINT']),
                               openai_api_version=config.get('openai_api_version',
                                                             LLM_ENV['azure']['OPENAI_API_VERSION']),
                               timeout=timeout)

    elif config['type'].lower() == 'google':
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(temperature=temperature, model=config['name'],
                                      google_api_key=LLM_ENV['google']['GOOGLE_API_KEY'],
                                      model_kwargs=model_kwargs, timeout=timeout)
    elif config['type'].lower() == 'oracle':
        from langchain_community.chat_models.oci_generative_ai import ChatOCIGenAI
        if not "max_tokens" in model_kwargs:
            model_kwargs['max_tokens'] = 4000
        return ChatOCIGenAI(
            model_id=config['name'],
            service_endpoint=LLM_ENV['oracle']['SERVICE_ENDPOINT'],
            compartment_id=LLM_ENV['oracle']['COMPARTMENT_ID'],
            model_kwargs=model_kwargs,
        )

    elif config['type'].lower() == 'anthropic_vertex':
        from langchain_google_vertexai.model_garden import ChatAnthropicVertex
        return ChatAnthropicVertex(temperature=temperature, model=config['name'],
                                   project=LLM_ENV['anthropic_vertex']['PROJECT_ID'],
                                   location=LLM_ENV['anthropic_vertex']['REGION'],
                                   model_kwargs=model_kwargs, timeout=timeout)

    elif config['type'].lower() == 'anthropic':
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(temperature=temperature, model=config['name'],
                             anthropic_api_key=LLM_ENV['anthropic']['ANTHROPIC_KEY'],
                             model_kwargs=model_kwargs, timeout=timeout)

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
