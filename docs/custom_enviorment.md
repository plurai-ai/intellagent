# Custom Environment Setup

This guide provides instructions for setting up a custom environment.

You should create a new config_env.yml file and define there the chatbot environment variables
```python
environment:
    prompt_path:  # Path to prompt
    tools_script: # Path to a script that include the tools functions 
    database_folder: # Path to database folder
    database_validators: # Optional! Path to the file with the validators functions
```

After defining properly all the variables, you can call:
```bash
python run --config_path <path to the config_env.yml file>
````

## Environment Variables

### `prompt_path`
This variable specifies the path to a prompt file. The file should be a simple text file (`.txt`) containing the desired prompt.

---

### `database_folder`
This variable specifies the path to a folder containing CSV files. Each CSV file represents a database table used by the system and must include at least one row as an example. It is recommended to provide meaningful and indicative names for the columns in each CSV file.

---

### `tools_file`
This variable specifies the path to a Python script containing all the agent tool functions. 

The tool functions must be implemented using one of the following approaches:
- **Using LangChain's `@tool` decorator**: [LangChain Tool Decorator Guide](https://python.langchain.com/docs/how_to/custom_tools/#tool-decorator)
- **Using LangChain's `StructuredTool`**: [LangChain StructuredTool Guide](https://python.langchain.com/docs/how_to/custom_tools/#structuredtool)

If the tool needs to access the database you should add to the function a variable 'data', and use langchain [InjectedState class](https://langchain-ai.github.io/langgraph/reference/prebuilt/#langgraph.prebuilt.tool_node.InjectedState). 
In the following way:
```python 
def tool_function(data: Annotated[dict, InjectedState("dataset")]):
```
**The data variable will contain a dictionary of dataframe, where the name is the table name (according to the csv file name in the database folder).**

Optionally, you can define a tool schema by creating a variable named `<function_name>_schema`. If no schema variable is provided, the system will infer the schema automatically.

**Example of a valid `tools_file`:**  
See [examples/airline/input/tools/agent_tools.py](examples/airline/input/tools/agent_tools.py) for reference.

---

### `database_validators` (optional)
This variable specifies the path to a Python script containing validation functions for database operations. These functions help validate the data before it is inserted into the database. 

To define a validation function, use the `@validator` decorator and specify the table the function applies to. Validation functions ensure data integrity by checking conditions such as duplicate entries or invalid formats.

**Example Validator Function:**

```python
from simulator.utils.file_reading import validator

@validator(table='users')
def user_id_validator(new_df, dataset):
    if 'users' not in dataset:
        return new_df, dataset
    users_dataset = dataset['users']
    for index, row in new_df.iterrows():
        if row['user_id'] in users_dataset.values:
            error_message = f"User id {row['user_id']} already exists in the users data. You should choose a different user id."
            raise ValueError(error_message)
    return new_df, dataset
```
- The `@validator` decorator requires the table name as an argument.
- The validator function is applied before new data is inserted into the database.