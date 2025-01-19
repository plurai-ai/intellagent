# Custom Chatbot Setup

This guide explains how to configure the chatbot agent in the simulator. Currently, two types of customizations are supported:
1. Modifying the LLM in the default tool-calling chatbot agent.
2. Providing your own **LangGraph**-based chatbot agent.

In the future, additional integrations will be available for platforms like crewAI and AutoGEN.
### Prerequisites:
Before customizing the chatbot, ensure the environment is set up by following the [instructions here](./custom_environment.md).
## Tool-Calling Agent

If you're using a basic tool-calling agent, the only required modification (apart from environment customization) is selecting the appropriate LLM.  
IntellAgent supports all LangChain-compatible tool supported LLMs. Simply define the LLM type and name in the [configuration file](.././config/config_default.yml) according to your chatbot settings:  

```yaml
llm_chat:
    type: ''
    name: ''
```

### Setting the System Prompt  

By default, the agent uses the system prompt specified in the [environment settings](./custom_environment.md#prompt_path), along with the welcome message:  
**"Hello! 👋 I'm here to help with any request you might have."**  

To customize the system prompt or the welcome message, you need to define `dialog_manager.chatbot_initial_messages` before running the simulator.  
The variable should be a `List[BaseMessage]` (a list of LangChain base messages).  

Here’s an example of how to modify the `run.py` main function to use a custom prompt:  

```python
from langchain_core.messages import AIMessage, SystemMessage

# Initialize the simulator executor with the environment configuration
executor = SimulatorExecutor(config, args.output_path)

# Load the dataset (default is the latest). To load a specific dataset, pass its path.
executor.load_dataset(args.dataset)

# Define the initial messages (system prompt and welcome message)
messages = [
    SystemMessage(content='Enter the chatbot system message here'),
    AIMessage(content="Hello, how can I help you?")
]

# Update the default initial messages
executor.dialog_manager.chatbot_initial_messages = messages

# Run the simulation on the dataset
executor.run_simulation()
```
## General LangGraph Agent

If your chatbot is based on LangGraph, you can customize the chatbot agent to fit your graph architecture. Ensure that your graph adheres to the following requirements:

-   The graph state must include the following (additional variables should be optional):
````python
messages: Annotated[list[AnyMessage]]
args: dict[Any]
 ````

- The `messages` list should contain all interactions between the user and the chatbot. If internal calls made by the chatbot need to be tracked (e.g., it was part of the provided policies), this can be done using tool-calling messages:
```python
from langchain_core.messages import AIMessage, ToolMessage

messages += [
    AIMessage(
        content="",
        tool_calls=[
            {'name': 'get_product_details', 'args': {'product_id': 'P2'}, 'id': '1', 'type': 'tool_call'}
        ]
    ),
    ToolMessage(content='The product is not available currently in the store')
]
 ```

- If certain tools require database access, the database will be in the graph state within the `args` variable under the `data` key.
If the tool is properly defined (see [custom tools](./custom_environment.md#tools_file) with the `data` variable decorated by `InjectedState`, the agent should include the variable before invoking the tool. Below is an example of how this is handled in the base tool graph implementation: [tool graph](../simulator/agents_graphs/langgraph_tool.py):
````python
for tool_call in state["messages"][-1].tool_calls:
    tool = self.tools_by_name[tool_call["name"]]
    all_tool_args = list(inspect.signature(tool.func).parameters)
    function_args = copy.deepcopy(tool_call["args"])
    if state['args'] is not None:
        function_args.update({k: v for k, v in state['args'].items()
                              if (k in all_tool_args) and (k not in function_args)})
        observation = tool.func(**function_args)
 ````

If you have a LangGraph compiled graph that satisfies these conditions, set it in `dialog_manager.chatbot` before running the simulator. Here's an example of how to modify the `run.py` main function to use a custom graph:

```python
# Initialize the simulator executor with the environment configuration
executor = SimulatorExecutor(config, args.output_path)

# Load the dataset (default is the latest). To load a specific dataset, pass its path.
executor.load_dataset(args.dataset)

# Set the chatbot graph
executor.dialog_manager.chatbot = chatbot

# Run the simulation on the dataset
executor.run_simulation()
```
To provide a system prompt to the agent, configure the `initial_messages` variable as described [here](./custom_chatbot.md#Setting-the-System-Prompt).