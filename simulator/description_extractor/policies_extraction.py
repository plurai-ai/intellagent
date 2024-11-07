import numpy as np
from langchain import hub
from typing import List
from pydantic import BaseModel, Field
from langchain_core.language_models.chat_models import BaseChatModel
from simulator.utils import set_llm_chain, batch_invoke, set_callbck

class Rank(BaseModel):
    """The Rank"""
    score: int = Field(description="The final score between 0-10")

class FlowsList(BaseModel):
    """The list of flows"""
    sub_flows: List[str] = Field(description="A list of sub-flows")

class Policy(BaseModel):
    """The policy"""
    policy: str = Field(description="The policy")
    category: str = Field(description="The category of the policy")
    challenge_score: int = Field(description="The challenge score of the policy")

class PoliciesList(BaseModel):
    """The policies list"""
    policies: List[Policy] = Field(description="A list of policies and guidelines")

class PoliciesGraphGenerator:
    """
    This class is responsible for generating policies
    """

    def __init__(self, llm: BaseChatModel, config: dict):
        """
        Initialize the descriptor generator.
        :param llm (BaseChatModel): The language model to use.
        :param config: The configuration of the class
        """
        self.config = config
        self.llm = llm
        if 'prompt_path' in config:
            with open(config['prompt_path'], 'r') as file:
                self.prompt = file.read().rstrip()
        elif 'prompt' in config:
            self.prompt = config['prompt']
        elif 'prompt_hub_name' in config:
            hub_key = config.get("prompt_hub_key", None)
            self.prompt = hub.pull(config['prompt_hub_name'], api_key=hub_key)
        else:
            raise ValueError("The system prompt is missing, you must provide either prompt, prompt_path or prompt_hub_name")

    def generate(self, override=False):
        """
        Generate the policies
        """
        if override or not  hasattr(self, 'flows'):
            self.flows = self.extract_flows()
        if override or not hasattr(self, 'policies'):
            self.policies = self.extract_policies()
        if override or not hasattr(self, 'relations'):
            self.relations = self.extract_graph()
        #self.relations = ''
        #self.init_graph()

    def extract_flows(self):
        """
        Extract the flows from the prompt
        """

        flow_extractor = set_llm_chain(self.llm, structure=FlowsList, **self.config['flow_config']['prompt'])
        flows = flow_extractor.invoke({'user_prompt': self.prompt})
        return flows.dict()['sub_flows']

    def extract_policies(self):
        """
        Extract the policies from the prompt
        """
        policy_extractor = set_llm_chain(self.llm, **self.config['policies_config']['prompt'], structure=PoliciesList)
        flows_policies = {}

        for flow in self.flows:
            cur_polices = policy_extractor.invoke({'user_prompt': self.prompt, 'flow': flow})
            flows_policies[flow] = cur_polices.dict()['policies']
        return flows_policies

    def extract_graph(self):
        """
        Extract the weighted relations between the policies
        """

        def policy_to_str(policy):
            return f"Flow: {policy['flow']}\npolicy: {policy['policy']}"

        edge_llm = set_llm_chain(self.llm, prompt_hub_name="eladlev/policies_graph", structure=Rank) #TODO: read from config
        callback = set_callbck('openai')
        samples_batch = []
        policies_list = []
        for flow, policies in self.policies.items():
            policies_list += [{'flow': flow, 'policy': policy['policy']} for policy in policies]

        for i, first_policy in enumerate(policies_list):
            for j, second_policy in enumerate(policies_list[i + 1:]):
                samples_batch.append({'policy1': policy_to_str(first_policy),
                                      'policy2': policy_to_str(second_policy),
                                      'ind1': i,
                                      'ind2': j+i+1})
        res = batch_invoke(edge_llm.invoke, samples_batch, num_workers=5, callback=callback)
        self.graph_nodes = policies_list
        self.graph_edges = np.eye(len(policies_list))*10
        total_cost = 0
        for result in res:
            if result['error'] is not None:
                print(f"Error in sample {result['index']}: {result['error']}")
                continue
            total_cost += result['usage']
            cur_sample = samples_batch[result['index']]
            self.graph_edges[cur_sample['ind1'],cur_sample['ind2']] = result['result'].score

        AA = 2


    def init_graph(self):
        """
        Initialize the relation graphs between all the policies.
        """
        def policy_to_str(policy):
            return f"Flow: {policy['flow']}\npolicy: {policy['policy']}"
        samples_batch = []
        for i, first_policy in enumerate(self.policies):
            for second_policy in self.policies[i + 1:]:
                samples_batch.append({'policy1': policy_to_str(first_policy), 'policy2': policy_to_str(second_policy)})
        edge_llm = set_llm_chain(self.llm, prompt_hub_name="eladlev/policies_graph", structure=Rank)
        callback = set_callbck('openai')
        samples_batch = samples_batch[:10]
        res = batch_invoke(edge_llm.invoke, samples_batch, num_workers=5, callback=callback)
        all_res = [t['result'].score for t in res]
        ind = [t['index'] for t in res if t['result'].score == 8]

    def __getstate__(self):
        # Return a dictionary of picklable attributes
        state = self.__dict__.copy()
        # Remove the non-pickable attribute
        del state['llm']
        return state

    # def __setstate__(self, state):
    #     # Restore the object's state from the state dictionary
    #     self.__dict__.update(state)
    #     # Restore or reinitialize the non-picklable attribute
    #     self.llm = MetaChain(self.config) #TODO: restore the llm



