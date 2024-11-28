# Step-by-Step Guide to Running the Airline Agent

## Step 1 - Configure the Simulator Run Parameters
Edit the `config/config_default.yml` file to set the paths for the airline agent. Here’s an example configuration:

```yaml
environment:
    prompt_path: 'examples/input/airline/wiki.md'  # Path to your agent's wiki/documentation
    tools_folder: 'examples/input/airline/tools'   # Path to your agent's tools
    database_folder: 'examples/input/airline/data' # Path to your data schema
    task_description:  # Infered automatically from the input data ; If you don't want to infer you can simply provide it in the field 'content'
```
The `examples/input/airline` folder contains the following structure:

```
examples/
└── airline/
    ├── wiki.md                       # Prompt for the airline agent
    ├── tools/                        # Directory containing all the agent tools 
    │   ├── agent_tools.py            # Python script containing all the agent tools
    │   ├── book_reservation_tool.py  # Python script containing the book reservation tool
    │   ├── update_reservation_baggages.py  # Tool to update baggage information
    │   ├── update_reservation_passengers.py  # Tool to update passenger information
    │   ├── cancel_reservation.py      # Tool to cancel a reservation
    └── data_scheme/                  # Directory containing data schema for the agent
        ├── flights.json              # Flights data scheme and example 
        └── reservation.json          # Reservation data scheme and example
        └── users.json                # Users data scheme and example
```

## Step 2 - Run the Simulator
To run the simulation, use the following command:

```bash
python run.py --output_path ./examples/airline/output/run_x 
```
This command will execute the simulation using the specified configuration and dataset, saving the results to `../output/airline/run_1`.

## Step 3 - Analyze Simulator Results
After the simulation completes, you can find the results in the specified output path directory (`examples/airline/output/run_0`). The structure will look like this:

```
experiments/
├── dataset__[timestamp]__exp_[n]/    # Experiment run folder
│   ├── experiment.log                # Detailed experiment execution logs
│   ├── config.yaml                   # Configuration used for this run
│   ├── prompt.txt                    # Prompt template used
│   ├── memory.db                     # Dialog memory database
│   └── results.csv                   # Evaluation results and metrics
│
datasets/
├── dataset__[timestamp].pickle       # Generated dataset snapshot
└── dataset.log                       # Dataset generation logs
│
policies_graph/
├── graph.log                         # Policy graph generation logs
└── descriptions_generator.pickle     # Generated descriptions and policies
```

### Output Files Overview
- **experiment.log**: Contains detailed logs of the experiment execution, including timestamps and any errors encountered during the run.
- **config.yaml**: This file holds the configuration settings that were used for this specific simulation run, allowing for easy replication of results.
- **prompt.txt**: The prompt template that was utilized during the simulation, which can be useful for understanding the context of the agent's responses.
- **memory.db**: A database file that stores the dialog memory, which can be analyzed to understand how the agent retained and utilized information throughout the simulation.
- **results.csv**: This file includes the evaluation results and metrics from the simulation, providing insights into the performance of the agent.

In addition to the experiment folder, you will find:
- **dataset__[timestamp].pickle**: A snapshot of the generated dataset at the time of the simulation, which can be used for further analysis or training.
- **dataset.log**: Logs related to the dataset generation process, detailing any issues or important events that occurred during this phase.
- **graph.log**: Logs related to the generation of the policy graph, which can help in understanding the decision-making process of the agent.
- **descriptions_generator.pickle**: A file containing the generated descriptions and policies, useful for reviewing the agent's learned behaviors and strategies.
