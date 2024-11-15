from simulator.env import Env
import os
from simulator.descriptor_generator import DescriptionGenerator
from simulator.events_generator import EventsGenerator
from simulator.dialog_manager import DialogManager
from simulator.utils.logger_config import update_file_handler, setup_logger, ConsoleColor, logger
import pickle
from simulator.utils.file_reading import get_latest_file
from datetime import datetime
from simulator.dataset_handler import Dataset
import yaml

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
            setup_logger(os.path.join(output_path, 'policies_graph', 'graph.log'))
            logger.info(f"{ConsoleColor.CYAN}Start Building the policies graph:{ConsoleColor.RESET}")
            descriptions_generator = DescriptionGenerator(environment=self.environment,
                                                          config=config['description_generator'])
            descriptions_generator.generate_policies_graph()
            logger.info(f"{ConsoleColor.CYAN}Finish Building the policies graph{ConsoleColor.RESET}")
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
            dataset_path = 'dataset' + '__' + dt_string + '.pickle'
        dataset_path = os.path.join(datasets_dir, dataset_path)
        self.dataset_handler.load_dataset(dataset_path)

    def run_simulation(self):
        """
        Run the simulation on the dataset.
        """
        if len(self.dataset_handler) == 0:
            logger.warning(f"{ConsoleColor.RED}The dataset is empty. Loading the last dataset...{ConsoleColor.RESET}")
            self.load_dataset()
        experiments_dir = os.path.join(self.output_path, 'experiments')
        experiment_name = self.dataset_handler.dataset_name + '__' + datetime.now().strftime("%d_%m_%Y_%H_%M_%S")
        experiments_dir = os.path.join(experiments_dir, experiment_name)
        os.mkdir(experiments_dir)
        ## Save the prompt and the config in the experiment folder
        with open(os.path.join(experiments_dir, 'prompt.txt'), "w") as file:
            file.write(self.environment.prompt)
        with open(os.path.join(experiments_dir, 'config.yaml'), "w") as file:
            yaml.dump(self.config, file)

        # init the dialog
        self.dialog_manager.init_dialog(experiments_dir)
        # Run the dialog
        records = self.dataset_handler.records
        num_batch = len(records) // self.config['batch_size']
        all_res = []
        total_cost = 0
        for i in range(num_batch):
            if total_cost > self.config['max_cost']:
                logger.warning(
                    f"{ConsoleColor.RED}The cost limit for the experiment is reached. "
                    f"Stopping the simulation.{ConsoleColor.RESET}")
                break
            logger.info(f"{ConsoleColor.WHITE}Running batch {i}...{ConsoleColor.RESET}")
            res, cost = self.dialog_manager.run_events(records[i * self.config['batch_size']:
                                                               (i + 1) * self.config['batch_size']])
            all_res.extend(res)
            total_cost += cost
        return all_res


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
