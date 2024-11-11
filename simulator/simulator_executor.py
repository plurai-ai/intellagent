from simulator.env import Env
from simulator.descriptor_generator import DescriptionGenerator
from simulator.events_generator import EventsGenerator
from simulator.dialogue_manager import DialogManager
import pickle

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
        self.config = config
        self.environment = Env(config['environment'])
        self.event_generator = EventsGenerator(llm_config=config['event_generator']['llm'], env=self.environment)
        self.descriptions_generator = DescriptionGenerator(environment=self.environment,
                                                           config=config['description_generator'])
        #self.descriptions_generator.generate_policies_graph()
        import pickle
        #pickle.dump(self.descriptions_generator, open("policies_generator.pickle", "wb"))
        self.descriptions_generator = pickle.load(open("policies_generator.pickle", "rb"))
        self.dialog_manager = DialogManager(config['dialogue_manager'], environment=self.environment)



    def run_simulation(self, num_samples=15):
        """
        Run the simulation.
        """
        #descriptions = self.descriptions_generator.sample_description(5, num_samples=num_samples)
        #pickle.dump(descriptions, open('res.pickle', 'wb'))
        descriptions = pickle.load(open('res.pickle', 'rb'))
        res = self.event_generator.description_to_event(descriptions[0])
        res = self.dialog_manager.run_event(res)




