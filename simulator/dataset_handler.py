import os.path
import logging
import numpy as np
from simulator.descriptor_generator import DescriptionGenerator
from simulator.events_generator import EventsGenerator
import pickle


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

    def __len__(self):
        """
        Return the number of samples in the dataset.
        """
        return len(self.records)

    def load_dataset(self, path: str):
        """
        Loading dataset
        :param path: path for the records
        """
        if os.path.isfile(path):
            self.records = pickle.load(open(path, 'rb'))
        else:
            logging.warning('Dataset dump not found, initializing from zero')
        self.dataset_name = os.path.splitext(os.path.basename(path))[0]
        n_samples = self.config['num_samples'] - len(self.records)  # Number of samples to generate
        if n_samples == 0:
            return

        # Equalizing the distribution of difficulty levels according to the gap between the target frequency and the actual frequency
        difficulty_distribution, _ = np.histogram([r.description.challenge_level for r in self.records],
                                                  bins=np.arange(self.config['min_difficult_level'] - 0.5,
                                                                 self.config['max_difficult_level'] + 1.5, 1))
        bins = list(range(self.config['min_difficult_level'], self.config['max_difficult_level'] + 1))

        target_frequency = (len(self.records) + n_samples) / len(difficulty_distribution)
        deficits = np.maximum(target_frequency - difficulty_distribution,
                              0)  # Only consider bins that are underrepresented
        total_deficit = deficits.sum()
        weights = deficits / total_deficit if total_deficit > 0 else np.zeros_like(deficits)

        challenge_complexity = np.random.choice(bins, size=n_samples, p=weights)
        descriptions = self.descriptions_generator.sample_description(challenge_complexity, num_samples=n_samples)
        events = self.event_generator.descriptions_to_events(descriptions)
        self.records.extend(events)
        pickle.dump(self.records, open(path, 'wb'))
