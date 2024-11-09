import os
import pandas as pd
from pathlib import Path
from simulator.utils import load_tools
from langchain import hub
import logging
from simulator.utils import set_llm_chain
from simulator.utils import get_llm


class Env:
    def __init__(self, config):
        self.config = config
        self.load_database()
        self.load_prompt()
        self.load_tools()

    def load_tools(self):
        """
        Load the tools from the tools folder
        :return:
        """
        self.tools, self.tools_schema = load_tools(self.config['tools_folder'])
        if self.tools_schema and not(len(self.tools) == len(self.tools_schema)):
            logging.warning(f"If providing a schema, make sure to provide a schema for each tool. Found {len(self.tools)} tools and {len(self.tools_schema)} schemas."
                            f"Using the default tools schema for all tools.")
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
            raise ValueError("The system prompt is missing, you must provide either prompt, prompt_path or prompt_hub_name")

        if 'content' in self.config['task_description']:
            self.task_description = self.config['task_description']
        else:
            llm = get_llm(self.config['task_description']['llm'])
            task_extractor = set_llm_chain(llm,  **self.config['task_description']['extraction_prompt'])
            self.task_description = task_extractor.invoke({'prompt': self.prompt}).content


    def load_database(self):
        """
        Load the database from the database folder. Assuming each database is in a separate json file
        :return:
        """
        all_data_files = [file for file in os.listdir(self.config['database_folder']) if file.endswith('.json')]
        all_data = {Path(file).stem: pd.read_json(os.path.join(self.config['database_folder'], file), orient='index') for file in all_data_files}
        self.data_schema = {Path(file).stem: list(data.columns) for file, data in all_data.items()}
        self.data_examples = {table: all_data[table].iloc[0].to_json() for table in all_data}

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