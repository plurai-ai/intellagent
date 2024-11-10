from simulator.env import Env
from simulator.descriptor_generator import DescriptionGenerator
from simulator.events_generator import EventsGenerator
from simulator.dialogue_manager import DialogManager

class SimulatorExecutor:
    """
    This class is responsible for executing simulation.
    """

    def __init__(self, config: dict):
        """
        Initialize the simulator executor.
        :param config: The simulator configuration.
        :param environment (Env): The environment of the simulator.
        """
        self.environment = Env(config['environment'])
        self.event_generator = EventsGenerator(llm_config=config['event_generator']['llm'], env=self.environment)
        self.dialog_manager = DialogManager(config['dialogue_manager'], environment=self.environment)

        self.descriptions_generator = DescriptionGenerator(environment=self.environment,
                                                           config=config['description_generator'])
        self.descriptions_generator.generate_policies_graph()


    def run_simulation(self, num_samples=15):
        """
        Run the simulation.
        """
        self.descriptions_generator.sample_description(12, num_samples=num_samples)
        self.descriptions_generator.expected_behaviour_refinement()
        self.event_generator.init_executors()
        self.dialog_executor.init_dialog()
        self.dialog.compile_graph()
        self.dialog_executor.run_dialog()





