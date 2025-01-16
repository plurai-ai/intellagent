from simulator.env import Env
import os
from simulator.dataset.descriptor_generator import DescriptionGenerator
from simulator.dataset.events_generator import EventsGenerator
from simulator.dialog.dialog_manager import DialogManager
from simulator.utils.logger_config import update_logger_file, setup_logger, ConsoleColor
import pickle
from simulator.utils.file_reading import get_latest_file
from datetime import datetime
from simulator.dataset.dataset_handler import Dataset
import yaml
import pandas as pd
import json
import uuid
from simulator.utils.analysis import get_dialog_policies
from simulator.healthcare_analytics import (
    RunSimulationEvent,
    AnalyzeSimulationResultsEvent,
    ExceptionEvent,
    track_event
)

logger = None


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
        global logger
        logger = setup_logger(os.path.join(output_path, 'policies_graph', 'graph.log'))
        if description_generator_path is None:
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
        self.simulator_results = None

    @staticmethod
    def generate_run_id():
        """Generate a unique random Run ID."""
        return f"run-{uuid.uuid4().hex}"

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
        update_logger_file(os.path.join(datasets_dir, 'dataset.log'))
        self.dataset_handler.load_dataset(dataset_path)

    def run_simulation(self, experiment_name=''):
        """
        Run the simulation on the dataset.
        """
        if len(self.dataset_handler) == 0:
            print(f"{ConsoleColor.BLUE}The dataset is empty. Loading the last dataset...{ConsoleColor.RESET}")
            self.load_dataset()
        experiments_dir = os.path.join(self.output_path, 'experiments')
        if experiment_name == '':
            experiment_name = 'exp_{}'.format(len(os.listdir(experiments_dir)) + 1)
        experiment_name = self.dataset_handler.dataset_name + '__' + experiment_name
        experiment_dir = os.path.join(experiments_dir, experiment_name)
        if not os.path.isdir(experiment_dir):
            os.mkdir(experiment_dir)
        update_logger_file(os.path.join(experiment_dir, 'experiment.log'))
        ## Save the prompt and the config in the experiment folder
        with open(os.path.join(experiment_dir, 'prompt.txt'), "w") as file:
            file.write(self.environment.prompt)
        with open(os.path.join(experiment_dir, 'config.yaml'), "w") as file:
            yaml.dump(self.config, file)
        json.dump(self.dataset_handler.descriptions_generator.policies,
                  open(os.path.join(experiment_dir, 'policies_info.json'), "w"))

        # init the dialog
        self.dialog_manager.init_dialog(experiment_dir)

        # Run the dialog
        mini_batch_size = self.config['dialog_manager']['mini_batch_size']
        records = self.dataset_handler.records
        num_records = len(records)

        if num_records == 0:
            logger.warning(f"{ConsoleColor.RED}No records found to process.{ConsoleColor.RESET}")
            return []  # or handle this case appropriately

        num_batch = num_records // mini_batch_size
        all_res = []
        total_cost = 0
        start_iteration = 0

        logger.info(f"{ConsoleColor.CYAN}Start running the simulator{ConsoleColor.RESET}")
        intermediate_res = os.path.join(experiment_dir, 'res_dump.pickle')
        if os.path.isfile(intermediate_res):
            all_res, start_iteration, total_cost = pickle.load(open(intermediate_res, 'rb'))
        # Handle batches
        for i in range(start_iteration, num_batch, 1):
            if total_cost > self.config['dialog_manager']['cost_limit']:
                logger.warning(
                    f"{ConsoleColor.RED}The cost limit for the experiment is reached. "
                    f"Stopping the simulation.{ConsoleColor.RESET}")
                break
            logger.info(f"{ConsoleColor.WHITE}Running batch {i}...{ConsoleColor.RESET}")
            res, cost = self.dialog_manager.run_events(records[i * mini_batch_size:
                                                               (i + 1) * mini_batch_size])
            all_res.extend(res)
            total_cost += cost
            pickle.dump((all_res, i + 1, total_cost), open(intermediate_res, 'wb'))

        # Handle remaining records if any
        remaining_records = records[num_batch * mini_batch_size:]
        if remaining_records:
            logger.info(f"{ConsoleColor.WHITE}Running remaining records...{ConsoleColor.RESET}")
            if total_cost <= self.config['dialog_manager']['cost_limit']:
                res, cost = self.dialog_manager.run_events(remaining_records)
                all_res.extend(res)
                total_cost += cost
            else:
                logger.warning(
                    f"{ConsoleColor.RED}The cost limit for the experiment is reached. "
                    f"Skipping remaining records.{ConsoleColor.RESET}")

        logger.info(f"{ConsoleColor.CYAN}Finish running the simulator{ConsoleColor.RESET}")
        track_event(RunSimulationEvent(cost=total_cost,
                                       n_dialogs=len(all_res),
                                       avg_n_user_messages_per_dialog=sum(
                                           len(entry['res']['user_messages']) for entry in all_res) / len(
                                           all_res) if all_res else 0,
                                       avg_n_chatbot_messages_per_dialog=sum(
                                           len(entry['res']['chatbot_messages']) for entry in all_res) / len(
                                           all_res) if all_res else 0,
                                       llm_critique=self.dialog_manager.config['critique_config']['llm'],
                                       llm_user=self.dialog_manager.config['llm_user'],
                                       llm_chat=self.dialog_manager.config['llm_chat']))
        logger.info(f"{ConsoleColor.CYAN}Analyzing the results{ConsoleColor.RESET}")
        self.analyze_results(all_res, experiment_dir)

    def analyze_results(self, results, experiment_dir):
        """
        Analyze the results of the simulation.
        """
        results = get_dialog_policies(self.config['analysis'], results, self.dataset_handler.records)
        all_rows = []
        valid_event_ind = []
        for r in results:
            try:
                cur_event = self.dataset_handler.records[r['event_id'] - 1]
                user_messages = r['res'].get('user_messages', [])
                stop_signal = r['res'].get('stop_signal', '')
                if not user_messages:
                    continue  # Skip if no user messages
                if 'FAILURE' in stop_signal:
                    score = 0
                elif 'SUCCESS' in stop_signal:
                    score = 1
                else:
                    score = -1

                cur_row = {
                    'id': r['event_id'],
                    'thread_id': r['res'].get('thread_id'),
                    'score': score,
                    'reason': r['res']['user_thoughts'][-1] if 'user_thoughts' in r['res'] else None,
                    'scenario': getattr(cur_event, 'scenario', None),
                    'expected_behaviour': getattr(cur_event.description, 'expected_behaviour', None),
                    'challenge_level': getattr(cur_event.description, 'challenge_level', None),
                    'tested_challenge_level': r.get('tested_challenge_level', None),
                    'policies': getattr(cur_event.description, 'policies', None),
                    'policies_in_dialog': r.get('tested_policies', None),
                    'violated_policies': r.get('violated_policies', [])
                }
                all_rows.append(cur_row)
                valid_event_ind.append(r['event_id'] - 1)
            except (KeyError, AttributeError, IndexError) as e:
                error_message = f"Skipping a result due to missing data: {e}"
                logger.info(f"{ConsoleColor.CYAN}{error_message}{ConsoleColor.RESET}")
                track_event(ExceptionEvent(exception_type=type(e).__name__,
                                           error_message=error_message))
                continue
        non_valid_rows = []
        for i, event in enumerate(self.dataset_handler.records):
            if i in valid_event_ind:
                continue
            cur_row = {'id': i + 1, 'score': 0, 'challenge_level': getattr(event.description, 'challenge_level', None)}
            non_valid_rows.append(cur_row)
        if all_rows:
            df = pd.DataFrame(all_rows)
            df.to_csv(os.path.join(experiment_dir, 'results.csv'), index=False)
            error_df = pd.DataFrame(non_valid_rows)
            error_df.to_csv(os.path.join(experiment_dir, 'err_events.csv'), index=False)
            failure_rate = (df['score'] == False).mean()
            track_event(
                AnalyzeSimulationResultsEvent(
                    failure_rate=failure_rate
                )
            )
            logger.info(f"{ConsoleColor.CYAN}Finish running results analysis{ConsoleColor.RESET}")
        else:
            logger.info(f"{ConsoleColor.CYAN}No rows to process. Results are empty.{ConsoleColor.RESET}")

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
