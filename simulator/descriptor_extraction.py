from langchain import hub
from typing import List
from pydantic import BaseModel, Field
import yaml
from simulator.utils import set_llm_chain, batch_invoke, set_callbck
import pickle
from typing import Tuple
from simulator.utils import get_llm
import networkx as nx
import random


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

class DescriptionGenerator:
    """
    This class is responsible for generating descriptions
    """

    def __init__(self, config: dict):
        """
        Initialize the descriptor generator.
        :param llm (BaseChatModel): The language model to use.
        :param config: The configuration of the class
        """
        self.config = config
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

    def generate_policies_graph(self, override=False):
        """
        Generate the policies graph
        """
        if override or not hasattr(self, 'flows'):
            self.flows = self.extract_flows()
        if override or not hasattr(self, 'policies'):
            self.policies = self.extract_policies()
        if override or not hasattr(self, 'relations'):
            self.extract_graph()

    def extract_flows(self):
        """
        Extract the flows from the prompt
        """
        llm = get_llm(self.config['llm_policy'])
        flow_extractor = set_llm_chain(llm, structure=FlowsList, **self.config['flow_config']['prompt'])
        flows = flow_extractor.invoke({'user_prompt': self.prompt})
        return flows.dict()['sub_flows']

    def extract_policies(self):
        """
        Extract the policies from the prompt
        """
        llm = get_llm(self.config['llm_policy'])
        policy_extractor = set_llm_chain(llm, **self.config['policies_config']['prompt'], structure=PoliciesList)
        flows_policies = {}

        for flow in self.flows:
            cur_polices = policy_extractor.invoke({'user_prompt': self.prompt, 'flow': flow})
            flows_policies[flow] = cur_polices.dict()['policies']
        return flows_policies

    def extract_graph(self):
        """
        Extract the weighted relations between the policies
        """
        llm = get_llm(self.config['llm_edge'])
        self.graph_info = {'G': nx.Graph()}
        def policy_to_str(policy):
            return f"Flow: {policy['flow']}\npolicy: {policy['policy']}"

        edge_llm = set_llm_chain(llm, structure=Rank, **self.config['edge_config']['prompt'])
        callback = set_callbck('openai')
        samples_batch = []
        policies_list = []
        for flow, policies in self.policies.items():
            policies_list += [{'flow': flow, 'policy': policy['policy'], 'score': policy['challenge_score']}
                              for policy in policies]
        for i, first_policy in enumerate(policies_list):
            for j, second_policy in enumerate(policies_list[i + 1:]):
                samples_batch.append({'policy1': policy_to_str(first_policy),
                                      'policy2': policy_to_str(second_policy),
                                      'ind1': i,
                                      'ind2': j+i+1})
        self.graph_info['nodes'] = policies_list
        res = batch_invoke(edge_llm.invoke, samples_batch, num_workers=5, callback=callback)
        total_cost = 0
        all_edges = []
        for result in res:
            if result['error'] is not None:
                print(f"Error in sample {result['index']}: {result['error']}")
                continue
            total_cost += result['usage']
            cur_sample = samples_batch[result['index']]
            all_edges.append((cur_sample['ind1'], cur_sample['ind2'], {'weight': result['result'].score}))

        self.graph_info['G'].add_edges_from(all_edges)

    def sample_from_graph(self, threshold) -> Tuple[list, int]:
        """
        Sample a path from the graph. Traverse the graph according to edge weight probability until the path sum exceeds the threshold.
        :param threshold:
        :return: list of nodes in the path and the path sum
        """
        # Start with a random node
        current_node = random.choice(list(self.graph_info['G'].nodes))
        path = [current_node]
        path_sum = self.graph_info['nodes'][current_node]['score']

        # Traverse until the path sum exceeds the threshold
        while path_sum <= threshold:
            # Get neighbors and weights for current node
            neighbors = list(self.graph_info['G'].neighbors(current_node))
            weights = [self.graph_info['G'][current_node][neighbor]['weight'] for neighbor in neighbors]

            # Weighted choice of the next node
            next_node = random.choices(neighbors, weights=weights)[0]

            # Add the chosen node to the path and update path sum
            path.append(next_node)
            path_sum += self.graph_info['nodes'][current_node]['score']

            # Move to the next node
            current_node = next_node
        return [self.graph_info['nodes'][t] for t in path], path_sum

    def sample_description(self, challenge_complexity) -> Tuple[str, dict, int]:
        """
        Sample a description of event
        :param challenge_complexity: The complexity of the generated description (it will be at least the provided number)
        :return: The description of the event, the list of policies that were used to generate the description and the actual complexity of the description
        """
        policies, path_sum = self.sample_from_graph(challenge_complexity)
        description = f"Challenge: {path_sum}\n"
        for policy in policies:
            description += f"Flow: {policy['flow']}\npolicy: {policy['policy']}\n"
        return description, policies, path_sum

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



