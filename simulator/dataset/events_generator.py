from agents.langgraph_tool import AgentTools
import pandas as pd
from agents.plan_and_execute import PlanExecuteImplementation
import json
from langchain import hub
from simulator.env import Env
from typing_extensions import Annotated
from langgraph.prebuilt import InjectedState
from langchain_core.tools.structured import StructuredTool
from simulator.dataset.definitions import *
from simulator.utils.llm_utils import dict_to_str, set_llm_chain
from agents.plan_and_execute import Plan
from simulator.utils.llm_utils import get_llm, set_callbck
from simulator.dataset.descriptor_generator import Description
from simulator.utils.parallelism import async_batch_invoke
from typing import Tuple

class EventsGenerator:
    """
    This class is responsible for generating events for the simulator.
    """

    def __init__(self, config: dict, env: Env):
        """
        Initialize the event generator.
        :param config: The language model config
        :param environment (Env): The environment of the simulator.
        """
        llm_config = config['llm']
        self.config = config
        self.llm = get_llm(llm_config)
        self.callbacks = [set_callbck(llm_config['type'])]
        self.data = {}
        self.env = env
        self.init_agent()
        self.num_workers = config['num_workers']
        self.timeout = config['timeout']
        self.llm_symbolic = set_llm_chain(self.llm, **config['symbolic_enrichment_config']['prompt'],
                                          structure=info_symbolic)
        self.llm_constraints = set_llm_chain(self.llm, **config['symbolic_constraints_config']['prompt'])

    def init_executors(self) -> dict[AgentTools]:
        """
        Initialize the database plane executors.
        :return: list[AgentTools]: The list of executors.
        """
        rows_data = self.env.data_examples
        table_insertion_tools = {}
        agent_executors = {}
        for table_name, example in rows_data.items():
            cur_tool, tool_schema = self.get_insertion_function(table_name)
            table_insertion_tools[table_name] = StructuredTool.from_function(
                cur_tool,
                None,
                name='add_row_to_table',
                description='Add a row to the table in json format. The row should be a **json string** with the same schema as in the provided example.',
                infer_schema=True,
            )

            system_messages = hub.pull("eladlev/event_executor")
            system_messages = system_messages.partial(schema=self.env.data_schema[table_name],
                                                              example=json.dumps(rows_data[table_name]))
            agent_executor = AgentTools(llm=self.llm, tools=[think, table_insertion_tools[table_name]],
                                        system_prompt=system_messages)
            agent_executors[table_name] = agent_executor
        return agent_executors

    def get_insertion_function(self, table_name: str):
        def tool_function(json_row: str, dataset: Annotated[dict, InjectedState("dataset")]):
            try:
                df = pd.DataFrame([json.loads(json_row)])
                if not table_name in dataset:
                    dataset[table_name] = pd.DataFrame()
                for validator in self.env.database_validators[table_name]:
                    df, dataset = validator(df, dataset)
                dataset[table_name] = pd.concat([dataset[table_name], df], ignore_index=True)
            except Exception as e:
                return f"Error: {e}"
            return f"Added row to {table_name} table"

        class add_row_input(BaseModel):
            json_row: str = "The row to insert, it must be as **string**"

        return tool_function, add_row_input

    def get_planner_prompt(self):
        prompt = hub.pull("eladlev/planner_event_generator")
        return prompt.partial(tables_info=dict_to_str(self.env.data_schema))

    def init_agent(self):
        """
        Initialize the agent.
        """
        planner = set_llm_chain(self.llm, prompt=self.get_planner_prompt(), structure=Plan)
        replanner = set_llm_chain(self.llm, prompt_hub_name="eladlev/replanner_event_generator", structure=Plan)
        self.agent = PlanExecuteImplementation(planner=planner,
                                               replanner=replanner,
                                               executor=self.init_executors())

    def description_to_event(self, description: Description) -> Event:
        """
        Generate an event based on the given description.
        """
        res = self.agent.invoke(input={'planner_input': {'symbolic_info': description.symbolic_info,
                                                         'tables_schema': dict_to_str(self.env.data_schema)},
                                       'args': {'dataset': {}}})
        event = Event(description=description, database=res['args']['dataset'], scenario=res['response'])
        return event

    async def adescription_to_event(self, description: Description) -> Event:
        """
        Generate an event based on the given description.
        """
        res = await self.agent.ainvoke(input={'input': description.event_description, 'args': {'dataset': {}}})
        event = Event(description=description, database=res['args']['dataset'], scenario=res['response'])
        return event

    def descriptions_to_symbolic(self, descriptions: list[Description]) -> tuple[list[EventSymbolic], float]:
        """
        Generate symbolic variables representations based on the given descriptions.
        :param descriptions: The descriptions of the events
        :return: The symbolic event including: enriched scenario with variables, symbolic variables list, the relations between the symbols, and tables rows.
                 The cost of the step.
        """
        samples_batch = []
        cost = 0
        schema = dict_to_str(self.env.data_schema)
        for i, description in enumerate(descriptions):
            samples_batch.append( {"tables_info": schema, 'scenario': description.event_description})
        num_workers = self.config['symbolic_enrichment_config'].get('num_workers', 1)
        timeout = self.config['symbolic_enrichment_config'].get('timeout', 40)
        res = async_batch_invoke(self.llm_symbolic.ainvoke, samples_batch, num_workers=num_workers,
                                 callbacks=self.callbacks, timeout=timeout)
        events_info = []
        for result in res:
            if result['error'] is not None:
                continue
            cost += result['usage']
            cur_event = EventSymbolic(symbolic_info=result['result'], description=descriptions[result['index']])
            events_info.append(cur_event)
        return events_info, cost

    def get_symbolic_constraints(self, events: list[EventSymbolic]) -> Tuple[list[EventSymbolic], float]:
        """
        Generate the policies constraints based on the given symbolic events.
        :param events: The symbolic events
        :return: The symbolic events with the policies constraints and the cost of the step.
        """
        samples_batch = []
        cost = 0
        for i, event in enumerate(events):
            samples_batch.append({"symbolic_info": str(event), 'system_prompt': self.env.prompt})
        num_workers = self.config['symbolic_constraints_config'].get('num_workers', 1)
        timeout = self.config['symbolic_constraints_config'].get('timeout', 40)
        res = async_batch_invoke(self.llm_constraints.ainvoke, samples_batch, num_workers=num_workers,
                                 callbacks=self.callbacks, timeout=timeout)
        for result in res:
            if result['error'] is not None:
                continue
            cost += result['usage']
            events[result['index']].policies_constraints = result['result'].content
        return events, cost


    def descriptions_to_events(self, descriptions: list[Description]) -> Tuple[list[Event], float]:
        """
        Generate events based on the given descriptions.
        """
        res = async_batch_invoke(self.adescription_to_event, descriptions, num_workers=self.num_workers,
                                 callbacks=self.callbacks, timeout=self.timeout)
        all_events = [r['result'] for r in res if r['error'] is None]
        total_cost = sum([r['usage'] for r in res if r['error'] is None])
        return all_events, total_cost
