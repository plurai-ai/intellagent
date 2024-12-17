## Installation

This guide provides detailed instructions for setting up your development environment, configuring LLMs, and integrating various tools necessary for your project.

## Prerequisites

- Python 3.10

## Step-by-Step Installation

### 1. Clone the Repository

```bash
git clone git@github.com:plurai-ai/Chat-Agent-Simulator.git
cd Chat-Agent-Simulator
```

### 2. Install Dependencies

Choose one of the following methods to install dependencies:

#### Using Conda
```bash
conda env create -f environment_dev.yml
conda activate Chat-Agent-Simulator
```

#### Using pip
```bash
pip install -r requirements.txt
```

#### Using pipenv
```bash
pip install pipenv
pipenv install
```

### 3. Configure LLM API Keys

Edit the `config/llm_env.yml` file with your API credentials:

```yaml
openai:
  OPENAI_API_KEY: "your-api-key-here"
  OPENAI_API_BASE: ''
  OPENAI_ORGANIZATION: ''

azure:
  AZURE_OPENAI_API_KEY: "your-api-key-here"
  AZURE_OPENAI_ENDPOINT: "your-endpoint"
  OPENAI_API_VERSION: "your-api-version"
```

### 4. Configure Simulator Parameters

Before running the simulator, configure the `config/config_default.yml` file. Key configuration sections include:

- `environment`: Paths for prompts, tools, and data-scheme folders
- `description_generator`: Settings for flow extraction and policies
- `event_generator`: LLM and worker configurations
- `dialog_manager`: Dialog system and LLM settings
- `dataset`: Parameters for dataset generation

Important configuration points:
1. Update file paths in the `environment` section
2. Configure LLM settings (`type` and `name`)
3. Adjust worker settings (`num_workers` and `timeout`)
4. Set appropriate `cost_limit` values

### 5. Run the Simulator

Use the following command to run the simulator:

```bash
python run.py --output_path <output_path> [--config_path <config_path>] [--dataset <dataset>]
```

Arguments:
- `--output_path`: (Required) Path for saving output files
- `--config_path`: (Optional) Path to config file (default: `config/config_default.yml`)
- `--dataset`: (Optional) Dataset name (default: `'latest'`)

Example:
```bash
python run.py --output_path ../output/exp1 --config_path ./config/config_airline.yml
```

### 6. View Results

After simulation completion, results will be organized in the following structure:

```
experiments/
├── dataset__[timestamp]__exp_[n]/    # Experiment run folder
│   ├── experiment.log                # Detailed execution logs
│   ├── config.yaml                   # Configuration used
│   ├── prompt.txt                    # Prompt template
│   ├── memory.db                     # Dialog memory database
│   └── results.csv                   # Evaluation results

datasets/
├── dataset__[timestamp].pickle       # Dataset snapshot
└── dataset.log                       # Generation logs

policies_graph/
├── graph.log                         # Policy graph logs
└── descriptions_generator.pickle     # Generated descriptions
```

To visualize the simulation results using streamlit, run:
```bash
cd simulator/visualization 
streamlit run Simulator_Visualizer.py
```
This will launch a Streamlit dashboard showing detailed analytics and visualizations of your simulation results.
```
