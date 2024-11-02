import os
import pandas as pd
from pathlib import Path
from simulator.utils import load_tools
import json
import logging


class Env:
    def __init__(self, config):
        self.config = config
        self.load_database()
        self.tools, self.tools_schema = load_tools(self.config['tools_folder'])
        if self.tools_schema and  not(len(self.tools) == len(self.tools_schema)):
            logging.warning(f"If providing a schema, make sure to provide a schema for each tool. Found {len(self.tools)} tools and {len(self.tools_schema)} schemas."
                            f"Using the default tools schema for all tools.")
            self.tools_schema = []
        self.user_prompt_args = self.config.get('user_prompt_args', {'prompt_hub_name': 'eladlev/user_sim'})
        self.chatbot_prompt_args = self.config['chatbot_prompt_args']

    def load_database(self):
        all_data_files = [file for file in os.listdir(self.config['data_folder']) if file.endswith('.json')]
        all_data = {Path(file).stem: pd.read_json(os.path.join(self.config['data_folder'], file), orient='index') for file in all_data_files}
        self.data_schema = {Path(file).stem: list(data.columns) for file, data in all_data.items()}
        self.data_examples = {table: all_data[table].iloc[0].to_json() for table in all_data}

    def step(self):
        self.time += 1
        for agent in self.agents:
            agent.step(self)
        self.done = self.time >= self.config.max_time

    def run(self):
        while not self.done:
            self.step()

    def reset(self):
        self.time = 0
        self.done = False
        for agent in self.agents:
            agent.reset()
        self.map.reset()

    def render(self):
        self.map.render(self.agents)
        print(f"Time: {self.time}")
        print(f"Agents: {self.agents}")
        print(f"Done: {self.done}")
        print()

    def close(self):
        pass

    def __str__(self):
        return f"Env(time={self.time}, done={self.done})"

    def __repr__(self):
        return str(self)