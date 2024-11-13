from simulator.env import Env
from simulator.descriptor_generator import DescriptionGenerator
from simulator.events_generator import EventsGenerator
from simulator.dialog_manager import DialogManager
from simulator.utils import batch_invoke
import pickle
from simulator.utils import get_latest_file
from datetime import datetime
from simulator.dataset_handler import Dataset


class SimulatorExecutor:
    """
    This class is responsible for executing simulation.
    """

    def __init__(self, config: dict, output_path: str):
        """
        Initialize the simulator executor.
        :param config: The simulator configuration.
        :param output_path: The artifacts output path.
        """
        self.config = config
        self.environment = Env(config['environment'])
        description_generator_path = self.set_output_folder(output_path)
        if description_generator_path is None:
            descriptions_generator = DescriptionGenerator(environment=self.environment,
                                                          config=config['description_generator'])
            descriptions_generator.generate_policies_graph()
            pickle.dump(descriptions_generator,
                        open(os.path.join(output_path, 'policies_graph', 'descriptions_generator.pickle'), 'wb'))
        else:
            descriptions_generator = pickle.load(
                open(os.path.join(output_path, 'policies_graph', 'descriptions_generator.pickle'), 'rb'))

        descriptions_generator = descriptions_generator
        event_generator = EventsGenerator(config=config['event_generator'], env=self.environment)
        self.dialog_manager = DialogManager(config['dialog_manager'], environment=self.environment)
        self.dataset_handler = Dataset(config['dataset'], event_generator=event_generator,
                                       descriptions_generator=descriptions_generator)
        self.output_path = output_path

    def load_dataset(self, dataset_path='latest'):
        """
        Load the dataset. If latest, load the latest dataset.
        :param dataset_path: The dataset path.
        """
        datasets_dir = os.path.join(self.output_path, 'datasets')
        if dataset_path == 'latest':
            dataset_path = get_latest_file(datasets_dir)
        if dataset_path is None:
            dt_string = datetime.now().strftime("%d_%m_%Y_%H_%M_%S")
            dataset_path = 'dataset' + '__' + dt_string + '.json'
        dataset_path = os.path.join(datasets_dir, dataset_path)
        self.dataset_handler.load_dataset(dataset_path)

    def run_simulation(self, num_samples=15):
        """
        Run the simulation.
        """
        #descriptions = self.descriptions_generator.sample_description(5, num_samples=num_samples)
        #pickle.dump(descriptions, open('res.pickle', 'wb'))
        descriptions = pickle.load(open('res.pickle', 'rb'))
        res = self.event_generator.description_to_event(descriptions[0])
        res = self.dialog_manager.run_event(res)



    @staticmethod
    def set_output_folder(output_path):
        # Create the output folder if it does not exist with all the subfolders
        description_generator_path = None
        if not os.path.exists(output_path):
            os.makedirs(output_path)
        if not os.path.exists(os.path.join(output_path, 'policies_graph')):
            os.makedirs(os.path.join(output_path, 'policies_graph'))
        if not os.path.exists(os.path.join(output_path, 'datasets')):
            os.makedirs(os.path.join(output_path, 'datasets'))
        if not os.path.exists(os.path.join(output_path, 'experiments')):
            os.makedirs(os.path.join(output_path, 'experiments'))
        if os.path.isfile(os.path.join(output_path, 'policies_graph', 'descriptions_generator.pickle')):
            description_generator_path = os.path.join(output_path, 'policies_graph', 'descriptions_generator.pickle')
        return description_generator_path
