# Step-by-Step Guide to Running the Airline Agent

## Step 1 - Configure the Simulator Run Parameters
Edit the `config/config_airline.yml` file to set the paths for the airline agent. Here’s an example configuration:

```yaml
environment:
    prompt_path: 'examples/input/airline/wiki.md'  # Path to your agent's wiki/documentation
    tools_file: 'examples/input/airline/tools/agent_tools.py'   # Path to your agent's tools 
    database_folder: 'examples/input/airline/data' # Path to your data schema
    database_validators: 'examples/airline/input/validators/data_validators.py' # Optional! Path to the file with the validators functions
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

## Step 2 - Run the Simulator and Understand the Output

### Running the Simulation
Execute the simulator using:
```bash
python run.py --config ./config/config_airline.yml --output_path ./examples/airline/output/run_1 
```

### Understanding the Descriptor Generator Output
The simulator processes your input in several stages:

2.0. **Task Description Generation**
   - Automatically inferred from the prompt (can be manually specified in `config_airline.yml`)
   - Defines the chatbot's role as an airline agent handling reservations within policy constraints

2.1. **Flow Extraction**
   The system identifies four main flows:
   - Book flight
   - Modify flight
   - Cancel flight
   - Refund

2.2. **Policy Extraction**
   Each flow has associated policies. Examples:

   | Flow | Policy Example | Category | Challenge Score |
   |------|---------------|-----------|-----------------|
   | Book Flight | Agent must obtain user ID, trip type, origin, and destination | Knowledge extraction | 2 |
   | Modify Flight | All reservations can change cabin without changing flights | Company policy | 2 |
   | Cancel Flight | Cancellation allowed within 24h of booking or airline cancellation | Logical Reasoning | 4 |
   | Refund | Compensation available for eligible members based on status/insurance | Company policy | 3 |

2.3. **Relations Graph Generation**
   - Creates a network of policy relationships
   - Nodes: Individual policies
   - Edges: Policy relationships
   - Weights: Combined challenge scores
   
   All descriptor data is saved to: `output_path/policies_graph/descriptions_generator.pickle`

2.4. **Events Generation**
The event generation process occurs in three stages:

2.4.1. **Symbolic Representation Generation**
   - Converts policies into symbolic format
   - Processes in parallel using multiple workers (configured in config)

2.4.2. **Symbolic Constraints Generation**
   - Creates constraints based on the symbolic representation
   - Uses same worker and timeout configuration as symbolic generation

2.4.3. **Event Graph Generation**
   - Final event creation (most time-intensive phase)
   - Includes restriction filtering, validation, and result compilation
   - Controlled by configurable difficulty levels
   - Generates samples in batches according to dataset configuration

All generated events are saved to: `output_path/datasets/dataset__[timestamp].pickle`

Note: Event generation is cost-controlled via the config settings.



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
- **dataset__[timestamp].pickle**: A snapshot of the generated dataset at the time of the simulation, which can be used for further analysis.
- **dataset.log**: Logs related to the dataset generation process, detailing any issues or important events that occurred during this phase.
- **graph.log**: Logs related to the generation of the policy graph, which can help in understanding the generated policies and their relations for the scenarios generation process.
- **descriptions_generator.pickle**: A file containing the generated descriptions and policies, useful for reviewing the agent's learned behaviors and strategies.


## Step 4 - Run the Simulator Visualization  
To visualize the simulation results using streamlit, run:
```bash
cd simulator/visualization 
streamlit run Simulator_Visualizer.py
```
This will launch a Streamlit dashboard showing detailed analytics and visualizations of your simulation results.
In the visualization you can:
- Load simulator memory and experiments by providing their full path
- View conversation flows and policy compliance
- Analyze agent performance and faliure points

Note: Make sure you have streamlit installed (`pip install streamlit`) before running the visualization.
