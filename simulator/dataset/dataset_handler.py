import os.path
from simulator.utils.logger_config import get_logger, ConsoleColor
import numpy as np
from simulator.dataset.descriptor_generator import DescriptionGenerator
from simulator.dataset.events_generator import EventsGenerator, Event
import pickle
from typing import List, Tuple
from statistics import mean, stdev
from simulator.healthcare_analytics import GenerateDatasetEvent, track_event


class Dataset:
    """
    This class store and manage all the dataset records (including annotations, predictions, etc.).
    """

    def __init__(self, config: dict, event_generator: EventsGenerator, descriptions_generator: DescriptionGenerator):
        """
        Initialize the dataset handler.
        :param config:
        :param event_generator:
        :param descriptions_generator:
        """
        self.config = config
        self.records = []
        self.event_generator = event_generator
        self.descriptions_generator = descriptions_generator
        self.dataset_name = None
        self.max_iterations = config['max_iterations']

    def __len__(self):
        """
        Return the number of samples in the dataset.
        """
        return len(self.records)

    def generate_mini_batch(self, batch_size: int) -> Tuple[List[Event], float]:
        logger = get_logger()
        # Equalizing the distribution of difficulty levels according to the gap between the target frequency and the actual frequency
        difficulty_distribution, _ = np.histogram([r.description.challenge_level for r in self.records],
                                                  bins=np.arange(self.config['min_difficult_level'] - 0.5,
                                                                 self.config['max_difficult_level'] + 1.5, 1))
        bins = list(range(self.config['min_difficult_level'], self.config['max_difficult_level'] + 1))

        target_frequency = (len(self.records) + batch_size) / len(difficulty_distribution)
        deficits = np.maximum(target_frequency - difficulty_distribution,
                              0)  # Only consider bins that are underrepresented
        total_deficit = deficits.sum()
        weights = deficits / total_deficit if total_deficit > 0 else np.zeros_like(deficits)

        challenge_complexity = np.random.choice(bins, size=batch_size, p=weights)
        logger.info(f'{ConsoleColor.CYAN}- Sample mini batch descriptions{ConsoleColor.RESET}')
        # Step 1: Generate descriptions
        descriptions, description_cost = self.descriptions_generator.sample_description(challenge_complexity,
                                                                                        num_samples=batch_size)
        if self.event_generator.env.data_schema:
            # Step 2: Generate symbolic variables
            logger.info(f'{ConsoleColor.CYAN}- Generate symbolic representation{ConsoleColor.RESET}')
            event_symbols, symbols_cost = self.event_generator.descriptions_to_symbolic(descriptions)
            # Step 3: Get symbols constraints
            logger.info(f'{ConsoleColor.CYAN}- Generate symbolic constraints{ConsoleColor.RESET}')
            event_symbols, events_constraints_cost = self.event_generator.get_symbolic_constraints(event_symbols)
            # Step 4: Generate the event (with the dataset)
            logger.info(f'{ConsoleColor.CYAN}- Generate the event (This would take a while...){ConsoleColor.RESET}')
            events, events_cost = self.event_generator.symbolics_to_events(event_symbols)
        else:  # No database!
            events = [Event(description=description,
                            database={}, scenario=description.event_description) for description in descriptions]
            events_cost, symbols_cost, events_constraints_cost = 0, 0, 0

        minibatch_cost = description_cost + symbols_cost + events_constraints_cost + events_cost
        return events, minibatch_cost

    def load_dataset(self, path: str):
        """
        Loading dataset
        :param path: path for the records
        """
        logger = get_logger()
        if os.path.isfile(path):
            self.records, iteration_num, dataset_cost = pickle.load(open(path, 'rb'))
        else:
            logger.warning(f"{ConsoleColor.RED}Dataset dump not found, initializing from zero{ConsoleColor.RESET}")
            iteration_num = 0
            dataset_cost = self.descriptions_generator.total_cost
        self.dataset_name = os.path.splitext(os.path.basename(path))[0]
        initial_n_samples = len(self.records)
        n_samples = self.config['num_samples'] - len(self.records)  # Number of samples to generate
        if n_samples <= 0:
            return
        logger.info(f'{ConsoleColor.CYAN}Start building the dataset{ConsoleColor.RESET}')
        dataset_generation_cost = 0
        initial_n_iterations = iteration_num
        while n_samples > 0 and iteration_num < self.max_iterations:
            if dataset_cost > self.config['cost_limit']:
                logger.warning(f"{ConsoleColor.RED}Cost is over the limit, stopping the generation. "
                               f"Increase the limit in the config file to generate more samples.{ConsoleColor.RESET}")
                return
            logger.info(f'{ConsoleColor.WHITE}Iteration {iteration_num} started{ConsoleColor.RESET}')
            cur_iteration_sample_size = min(self.config['mini_batch_size'], n_samples)
            events, minibatch_cost = self.generate_mini_batch(cur_iteration_sample_size)
            dataset_cost += minibatch_cost
            dataset_generation_cost += minibatch_cost
            for i, e in enumerate(events):
                e.id = len(self.records) + i + 1
            self.records.extend(events)
            n_samples -= len(events)
            iteration_num += 1
            pickle.dump((self.records, iteration_num, dataset_cost), open(path, 'wb'))
        challenge_scores = [r.description.challenge_level for r in self.records]
        average_challenge_level = mean(challenge_scores)
        std_challenge_level = stdev(challenge_scores) if len(challenge_scores) > 1 else 0
        avg_n_policies = mean(len(r.description.policies) for r in self.records)
        track_event(GenerateDatasetEvent(cost=dataset_generation_cost,
                                         initial_n_samples=initial_n_samples,
                                         total_n_samples=len(self.records),
                                         initial_n_iterations=initial_n_iterations,
                                         total_n_iterations=iteration_num,
                                         avg_challenge_score=average_challenge_level,
                                         std_challenge_score=std_challenge_level,
                                         avg_n_policies=avg_n_policies,
                                         llm_description_generator=self.descriptions_generator.config['llm_description'],
                                         llm_description_refinement=self.descriptions_generator.config['llm_refinement'],
                                         llm_event_graph_generator=self.event_generator.config["event_graph"]["llm"]))
        logger.info(f'{ConsoleColor.CYAN}Finish building the dataset{ConsoleColor.RESET}')
