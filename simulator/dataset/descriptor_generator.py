from typing import List
from pydantic import BaseModel, Field
from simulator.utils.llm_utils import set_llm_chain, set_callback
from simulator.utils.parallelism import batch_invoke, async_batch_invoke
from typing import Tuple
from simulator.utils.llm_utils import get_llm
import networkx as nx
import random, math
from simulator.env import Env
from dataclasses import dataclass
from simulator.utils.logger_config import ConsoleColor, get_logger

from simulator.healthcare_analytics import (
    ExtractFlowEvent,
    ExtractFlowPoliciesEvent,
    GenerateRelationsGraphEvent,
    track_event
)


def policies_list_to_str(policies):
    return "\n".join([f"Policy {i} flow: {policy['flow']}\nPolicy {i} content: {policy['policy']}\n------" for
                      i, policy in enumerate(policies)])


class Rank(BaseModel):
    """The Rank"""
    score: int = Field(description="The final score between 0-10")


class FlowsList(BaseModel):
    """The list of flows"""
    flows: List[str] = Field(description="A list of flows families")


class Policy(BaseModel):
    """The policy"""
    policy: str = Field(description="The policy")
    category: str = Field(description="The fine-grained category of the policy")
    challenge_score: int = Field(description="The challenge score of the policy between 1-5")


class PoliciesList(BaseModel):
    """The policies list"""
    policies: List[Policy] = Field(description="A list of policies and guidelines")


class EventDescription(BaseModel):
    event_description: str = Field(description="The event description")
    expected_behaviour: str = Field(description="The expected behaviour of the chatbot according to the policies")


@dataclass
class Description:
    """
    The description of the event
    """
    event_description: str
    expected_behaviour: str
    policies: List[str]
    challenge_level: int
    symbolic_info: str = None
    symbolic_restrictions: str = None


class DescriptionGenerator:
    """
    This class is responsible for generating descriptions
    """

    def __init__(self, config: dict, environment: Env):
        """
        Initialize the descriptor generator.
        :param llm (BaseChatModel): The language model to use.
        :param config: The configuration of the class
        :param environment: The environment of the simulator
        """
        self.config = config
        self.total_cost = 0
        self.prompt = environment.prompt
        self.task_description = environment.get_task_description()
        llm = get_llm(self.config['llm_description'])
        self.llm_description = set_llm_chain(llm, structure=EventDescription,
                                             **self.config['description_config']['prompt'])
        if self.config['refinement_config']['do_refinement']:
            llm = get_llm(self.config['llm_refinement'])
            self.feedback_chain = set_llm_chain(llm, **self.config['refinement_config']['prompt_feedback'])
            self.refinement_chain = set_llm_chain(llm, **self.config['refinement_config']['prompt_refinement'])

    def generate_policies_graph(self, override=False):
        """
        Generate the policies graph
        """
        logger = get_logger()
        if override or not hasattr(self, 'flows'):
            logger.info(f"{ConsoleColor.WHITE}Step 1: Breaking prompt to flows{ConsoleColor.RESET}")
            self.flows = self.extract_flows()
            logger.info(f"{ConsoleColor.WHITE}Finish step 1{ConsoleColor.RESET}")
        if override or not hasattr(self, 'policies'):
            logger.info(f"{ConsoleColor.WHITE}Step 2: Breaking each flow to policies{ConsoleColor.RESET}")
            self.policies = self.extract_policies()
            logger.info(f"{ConsoleColor.WHITE}Finish step 2{ConsoleColor.RESET}")
        if override or not hasattr(self, 'relations'):
            logger.info(f"{ConsoleColor.WHITE}Step 3: Building the relations graph{ConsoleColor.RESET}")
            self.extract_graph()
            logger.info(f"{ConsoleColor.WHITE}Finish step 3{ConsoleColor.RESET}")

    def extract_flows(self):
        """
        Extract the flows from the prompt
        """
        if len(self.prompt.split(' ')) < 300:  # Very short prompt, no need to split to flows. TODO: Change magic number
            return ['Conversation with the chatbot']
        llm = get_llm(self.config['llm_policy'])
        flow_extractor = set_llm_chain(llm, structure=FlowsList, **self.config['flow_config']['prompt'])
        result = batch_invoke(flow_extractor.invoke,
                              [{'user_prompt': self.prompt}], num_workers=1,
                              callbacks=[set_callback(self.config['llm_policy']['type'])])[0]
        self.total_cost += result['usage']
        flows = result['result']
        error_message = result['error']
        track_event(ExtractFlowEvent(cost=result['usage'],
                                     n_flows=len(flows.dict()['flows']),
                                     prompt_length=len(self.prompt),
                                     llm_policy=self.config['llm_policy'],
                                     error_message=error_message))
        return flows.dict()['flows']

    def extract_policies(self):
        """
        Extract the policies from the prompt
        """
        llm = get_llm(self.config['llm_policy'])
        policy_extractor = set_llm_chain(llm, **self.config['policies_config']['prompt'], structure=PoliciesList)
        flows_policies = {}
        batch = []
        for flow in self.flows:
            batch.append({'user_prompt': self.prompt, 'flow': flow})
        res = batch_invoke(policy_extractor.invoke, batch,
                           num_workers=self.config['policies_config']['num_workers'],
                           callbacks=[set_callback(self.config['llm_policy']['type'])])
        extract_policies_cost = 0
        batch_error_message = None
        n_policies_per_flow = []
        for i, result in enumerate(res):
            if result['error'] is not None:
                print(f"Error in sample {result['index']}: {result['error']}")
                batch_error_message = (batch_error_message or "") + f"flow {result['index']}: {result['error']} "
                continue

            # Accumulate usage cost
            extract_policies_cost += result.get('usage', 0)

            # Update flows_policies and calculate the number of policies
            flow_key = self.flows[result['index']]
            policies = result['result'].dict().get('policies', [])
            flows_policies[flow_key] = policies
            n_policies_per_flow.append(len(policies) if policies is not None else None)

        # Update the total cost
        self.total_cost += extract_policies_cost
        track_event(ExtractFlowPoliciesEvent(cost=extract_policies_cost,
                                             n_policies_per_flow=n_policies_per_flow,
                                             llm_policy=self.config['llm_policy'],
                                             error_message=batch_error_message
                                             )
                    )
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
        callback = set_callback(self.config['llm_edge']['type'])
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
                                      'ind2': j + i + 1})
        self.graph_info['nodes'] = policies_list
        num_workers = self.config['edge_config'].get('num_workers', 1)
        timeout = self.config['edge_config'].get('timeout', 10)
        res = async_batch_invoke(edge_llm.ainvoke, samples_batch, num_workers=num_workers,
                                 callbacks=[callback], timeout=timeout)
        all_edges = []
        graph_creation_cost = 0
        batch_error_message = None
        for result in res:
            if result['error'] is not None:
                print(f"Error in sample {result['index']}: {result['error']}")
                batch_error_message = (batch_error_message or "") + f"edge {result['index']}: {result['error']} "
                continue
            graph_creation_cost += result['usage']
            cur_sample = samples_batch[result['index']]
            all_edges.append((cur_sample['ind1'], cur_sample['ind2'], {'weight': result['result'].score}))
        self.total_cost += graph_creation_cost
        n_edges = len(all_edges)
        avg_edge_weight = sum(edge[2]['weight'] for edge in all_edges) / n_edges
        # Calculate standard deviation
        std_edge_weight = math.sqrt(sum((edge[2]['weight'] - avg_edge_weight) ** 2 for edge in all_edges) / n_edges)
        self.graph_info['G'].add_edges_from(all_edges)
        track_event(GenerateRelationsGraphEvent(cost=graph_creation_cost,
                                                n_edges=n_edges,
                                                avg_edge_weight=avg_edge_weight,
                                                std_edge_weight=std_edge_weight,
                                                llm_edge=self.config['llm_edge'],
                                                error_message=batch_error_message
                                                ))

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
        while path_sum < threshold:
            # Get neighbors and weights for current node
            neighbors = list(self.graph_info['G'].neighbors(current_node))
            neighbors = [neighbor for neighbor in neighbors if neighbor not in path]
            weights = [self.graph_info['G'][current_node][neighbor]['weight'] for neighbor in neighbors]

            # Weighted choice of the next node
            next_node = random.choices(neighbors, weights=weights)[0]

            # Add the chosen node to the path and update path sum
            path.append(next_node)
            path_sum += self.graph_info['nodes'][next_node]['score']

            # Move to the next node
            current_node = next_node
        return [self.graph_info['nodes'][t] for t in path], path_sum

    def sample_description(self, challenge_complexity: int or list[int], num_samples: int = 1) -> Tuple[list[Description], float]:
        """
        Sample a description of event
        :param challenge_complexity: The complexity of the generated description
        (it will be at least the provided number), either list with size num_samples or a single number
        :param num_samples: The number of samples to generate
        :return: The description of the event, the list of policies that were used to generate the description and the
        actual complexity of the description + the cost
        """

        if isinstance(challenge_complexity, int):
            challenge_complexity = [challenge_complexity] * num_samples
        elif len(challenge_complexity) != num_samples:
            raise ValueError(
                "The challenge complexity should be either a single number or a list of numbers with the same length as num_samples")

        samples_batch = []
        all_policies = []
        cost = 0
        for i, cur_score in enumerate(challenge_complexity):
            policies, path_sum = self.sample_from_graph(cur_score)
            all_policies.append({'policies': policies, 'path_sum': path_sum})
            samples_batch.append({'task_description': self.task_description,
                                  'policies': policies_list_to_str(policies)})
        num_workers = self.config['description_config'].get('num_workers', 1)
        timeout = self.config['description_config'].get('timeout', 10)
        callback = set_callback(self.config['llm_description']['type'])
        res = async_batch_invoke(self.llm_description.ainvoke, samples_batch, num_workers=num_workers,
                                 callbacks=[callback], timeout=timeout)
        for result in res:
            if result['error'] is not None:
                continue
            cost += result['usage']
            all_policies[result['index']]['description'] = result['result'].event_description
            all_policies[result['index']]['expected_behaviour'] = result['result'].expected_behaviour
        all_policies = [policy for policy in all_policies if 'description' in policy]
        descriptions = [Description(event_description=policy['description'],
                                    expected_behaviour=policy['expected_behaviour'],
                                    policies=policy['policies'],
                                    challenge_level=policy['path_sum']) for policy in all_policies]
        refinement_cost = 0
        if self.config['refinement_config']['do_refinement']:
            descriptions, refinement_cost = self.expected_behaviour_refinement(descriptions)
        cost += refinement_cost
        return descriptions, cost

    def expected_behaviour_refinement(self, descriptions: list[Description], num_iterations=1) -> Tuple[
        list[Description], float]:
        """
        Verify the expected behaviour of the chatbot according to each policy
        :param descriptions:
        :param num_iterations:
        :return: new updated descriptions list, and cost
        """
        iteration_indices = list(range(len(descriptions)))
        num_workers = self.config['refinement_config'].get('num_workers', 5)
        timeout = self.config['refinement_config'].get('timeout', 10)
        callback = set_callback(self.config['llm_refinement']['type'])
        cost = 0

        for i in range(num_iterations):
            batch_input = []
            # Step 1: provide feedback
            for ind in iteration_indices:
                batch_input.append({'description': descriptions[ind].event_description,
                                    'behaviour': descriptions[ind].expected_behaviour,
                                    'prompt': self.prompt})
            res = async_batch_invoke(self.feedback_chain.ainvoke, batch_input, num_workers=num_workers,
                                     callbacks=[callback], timeout=timeout)
            cur_refine_indices = []
            improved_batch = []
            # refine the behaviour
            for j, result in enumerate(res):
                if result['error'] is not None or 'None' in result['result'].content:
                    continue
                else:
                    cur_refine_indices.append(iteration_indices[result['index']])
                    cur_batch = batch_input[result['index']]
                    cur_batch['feedback'] = result['result'].content
                    improved_batch.append(cur_batch)
                    cost += result['usage']

            res = async_batch_invoke(self.refinement_chain.ainvoke, improved_batch, num_workers=num_workers,
                                     callbacks=[callback], timeout=timeout)
            for j, result in enumerate(res):
                if result['error'] is not None or 'None' in result['result'].content:
                    continue
                else:
                    descriptions[cur_refine_indices[result['index']]].expected_behaviour = result['result'].content
                    cost += result['usage']
            iteration_indices = cur_refine_indices
        return descriptions, cost

    def __getstate__(self):
        # Return a dictionary of picklable attributes
        state = self.__dict__.copy()
        # Remove the non-picklable attribute
        del state['llm_description']
        if 'feedback_chain' in state:
            del state['feedback_chain']
        if 'refinement_chain' in state:
            del state['refinement_chain']
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)
        llm = get_llm(self.config['llm_description'])
        self.llm_description = set_llm_chain(llm, structure=EventDescription,
                                             **self.config['description_config']['prompt'])
        if self.config['refinement_config']['do_refinement']:
            llm = get_llm(self.config['llm_refinement'])
            self.feedback_chain = set_llm_chain(llm, **self.config['refinement_config']['prompt_feedback'])
            self.refinement_chain = set_llm_chain(llm, **self.config['refinement_config']['prompt_refinement'])
        return self
