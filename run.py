import argparse
from simulator.utils.file_reading import override_config
from simulator.simulator_executor import SimulatorExecutor

def parse_args():
    parser = argparse.ArgumentParser(description="Process some integers.")
    parser.add_argument('--config_path', type=str, default='config/config_default.yml',
                        help="The configuration diff file path.")
    parser.add_argument('--output_path', type=str, required=True, help="Path to the output file.")
    return parser.parse_args()


def main():
    args = parse_args()
    config = override_config(args.config_path)
    # loading the simulator executor with the environment
    executor = SimulatorExecutor(config, args.output_path)
    # Loading the dataset default is latest, if you want to load a specific dataset, pass the path
    executor.load_dataset()
    # Run the simulation on the dataset
    executor.run_simulation()
    print("Processing complete.")


if __name__ == "__main__":
    main()
