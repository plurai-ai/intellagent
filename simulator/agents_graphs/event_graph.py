from langchain_core.runnables.base import Runnable
from langgraph.graph import END
from langgraph.graph import StateGraph, START
from typing_extensions import TypedDict
from typing import Optional, List
from simulator.agents_graphs.langgraph_tool import AgentTools
from simulator.utils.llm_utils import dict_to_str, load_yaml_content, data_to_str
import yaml


class EventState(TypedDict):
    rows_to_generate: list[str]
    rows_generated: list[str]
    event_description: str
    variables_definitions: str  # json representation to run in async
    cur_restrictions: Optional[str]
    dataset: Optional[str]
    all_restrictions: Optional[str]
    final_response_scenario: Optional[str]
    final_response_table_rows: Optional[List[str]]


class EventGraph:
    """
    Building the Events with the database for the simulator
    """

    def __init__(self, executors: dict[AgentTools],
                 llm_filter_constraints: Runnable,
                 llm_final_response: Runnable,
                 memory=None):
        """
        Initialize the event generator.]
        :param user (Runnable): The user model
        :param llm_filter_constraints (Runnable): The constraints chain
        :param llm_final_Response (Runnable): The final response chain
        :param memory (optional): The memory to store the conversations artifacts
        """
        self.executors = executors
        self.llm_filter_constraints = llm_filter_constraints
        self.llm_final_response = llm_final_response
        self.memory = memory
        self.compile_graph()

    def get_end_condition(self):
        def should_end(state: EventState):
            if not state['rows_to_generate']:
                return "final_response_node"
            else:
                return "executor"

        return should_end

    def get_executor_node(self):
        def executor_node(state):
            if not state['rows_to_generate']:
                return
            cur_row = state['rows_to_generate'].pop(0)
            cur_restrictions = state['cur_restrictions'] if state['cur_restrictions'] is not None \
                else state['all_restrictions']  # Get the current restrictions on the row
            executor_system_prompt = self.executors[cur_row['table_name']].system_prompt
            executor_messages = executor_system_prompt.format_messages(**{'row': cur_row['row'],
                                                                          'restrictions': cur_restrictions})
            res = self.executors[cur_row['table_name']].invoke({'messages': executor_messages,
                                                               'args': {'dataset': state['dataset']}},
                                                               config={'recursion_limit': 15})
            state['rows_generated'].append(cur_row)
            cur_dataset = res['args']['dataset']
            last_var = load_yaml_content(res['messages'][-1].content)
            variable_definitions = yaml.safe_load(state['variables_definitions'])
            if variable_definitions is None:
                variable_definitions = {}
            variable_definitions.update(last_var)
            return {"rows_to_generate": state['rows_to_generate'], 'rows_generated': state['rows_generated'],
                    'variables_definitions': yaml.dump(variable_definitions), 'dataset': cur_dataset}

        return executor_node

    def get_restriction_node(self):
        def restriction_node(state):
            if not state['rows_to_generate']:
                return
            cur_row = state['rows_to_generate'][0]['row']
            restrictions = state['all_restrictions']
            variables_str = yaml.safe_load(state['variables_definitions'])
            if variables_str is None:
                variables_str = ''
            else:
                variables_str = dict_to_str(variables_str)
            filter_constraints = self.llm_filter_constraints.invoke({'row': cur_row, 'restrictions': restrictions,
                                                                     'variables': variables_str})
            return {"cur_restrictions": filter_constraints.content}

        return restriction_node

    def get_final_node(self):
        def final_node(state):
            tables_str = data_to_str(state['dataset'])
            variables_str = dict_to_str(yaml.safe_load(state['variables_definitions']))
            final_res = self.llm_final_response.invoke({'scenario': state['event_description'],
                                                        'rows': tables_str,
                                                        'values': variables_str})
            final_res = final_res.dict()
            return {"final_response_scenario": final_res['scenario'],
                    'final_response_table_rows': tables_str}

        return final_node

    def compile_graph(self):
        workflow = StateGraph(EventState)
        workflow.add_node("executor", self.get_executor_node())
        workflow.add_node("restriction", self.get_restriction_node())
        workflow.add_node("final_response_node", self.get_final_node())
        workflow.add_edge(START, "restriction")
        workflow.add_conditional_edges(
            "restriction",
            self.get_end_condition(),
            ["executor", 'final_response_node'],
        )
        workflow.add_edge('executor', "restriction")
        workflow.add_edge('final_response_node', END)
        self.graph = workflow.compile()

    def invoke(self, **kwargs):
        """
        Invoke the agent with the messages
        :return:
        """
        return self.graph.invoke(input=kwargs)

    def ainvoke(self, **kwargs):
        """
        async Invoke the agent with the messages
        :return:
        """
        return self.graph.ainvoke(input=kwargs)
