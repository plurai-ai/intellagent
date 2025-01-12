import os
import pandas as pd
from pathlib import Path
from simulator.utils.llm_utils import load_tools, set_llm_chain, get_llm
from langchain import hub
from simulator.utils.logger_config import get_logger, ConsoleColor
from simulator.utils.file_reading import get_validators_from_module


class Env:
    def __init__(self, config):
        self.config = config
        self.data_schema = {}
        self.data_examples = {}
        self.database_validators = {}
        self.load_database()
        self.load_prompt()
        self.load_tools()

    def load_tools(self):
        """
        Load the tools from the tools folder
        :return:
        """
        logger = get_logger()
        self.tools, self.tools_schema = load_tools(self.config['tools_file'])
        if self.tools_schema and not (len(self.tools) == len(self.tools_schema)):
            logger.warning(
                f"{ConsoleColor.RED}If providing a schema, make sure to provide a schema for each tool. Found {len(self.tools)} tools and {len(self.tools_schema)} schemas."
                f"Using the default tools schema for all tools.{ConsoleColor.RESET}")
            self.tools_schema = []

    def load_prompt(self):
        """
        Load the prompt from the prompt path
        :return:
        """
        if 'prompt_path' in self.config:
            with open(self.config['prompt_path'], 'r') as file:
                self.prompt = file.read().rstrip()
        elif 'prompt' in self.config:
            self.prompt = self.config['prompt']
        elif 'prompt_hub_name' in self.config:
            hub_key = self.config.get("prompt_hub_key", None)
            self.prompt = hub.pull(self.config['prompt_hub_name'], api_key=hub_key)
        else:
            raise ValueError(
                "The system prompt is missing, you must provide either prompt, prompt_path or prompt_hub_name")

        if 'content' in self.config['task_description']:
            self.task_description = self.config['task_description']
        else:
            self.task_description = None

    def get_task_description(self):
        """Generate task description if not exists"""
        if self.task_description is None:
            llm = get_llm(self.config['task_description']['llm'])
            task_extractor = set_llm_chain(llm, **self.config['task_description']['extraction_prompt'])
            self.task_description = task_extractor.invoke({'prompt': self.prompt}).content
        return self.task_description

    def load_database(self):
        """
        Load the database from the database folder. Assuming each database is in a separate json file
        :return:
        """
        logger = get_logger()
        if 'database_folder' not in self.config or not os.path.exists(self.config['database_folder']):
            logger.warning(
                f"{ConsoleColor.RED}Database folder not found. No database loaded.{ConsoleColor.RESET}")
            return {}
        all_data_files = [file for file in os.listdir(self.config['database_folder'])
                          if file.endswith('.json') or file.endswith('.csv')]
        all_data = {}
        for file in all_data_files:
            if file.endswith('.json'):
                table = pd.read_json(os.path.join(self.config['database_folder'], file), orient='index')
            else:
                table = pd.read_csv(os.path.join(self.config['database_folder'], file))
            all_data[Path(file).stem] = table

        self.data_schema = {Path(file).stem: list(data.columns) for file, data in all_data.items()}
        self.data_examples = {table: all_data[table].iloc[0].to_json() for table in all_data}
        database_validators_path = self.config.get('database_validators', None)
        if database_validators_path is not None:
            self.database_validators = {table: get_validators_from_module(database_validators_path, table) for table in
                                        all_data}
        else:
            self.database_validators = {table: [] for table in all_data}

    def get_policies(self):
        pass

    def __getstate__(self):
        # Return a dictionary of picklable attributes
        state = self.__dict__.copy()
        # Remove the non-picklable attribute
        del state['tools']
        del state['tools_schema']
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)
        self.load_tools()
        return self
