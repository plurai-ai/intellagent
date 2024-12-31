# Custom Chat-Agent Environment Setup

This guide provides instructions for setting up a custom environment.

You should create a new config_env.yml file and define there the chatbot environment variables
```python
environment:
    prompt_path:  # Path to prompt
    tools_file: # Path to a python script that include all the tools functions 
    database_folder: # Path to database folder
    database_validators: # Optional! Path to the file with the validators functions
```
After defining properly all the variables, you can run the simulator on the new custom environment:
```bash
python run.py \
    --output_path PATH     # Required: Directory where output files will be saved
    --config_path PATH     # Optional: Path to config_env.yml (default: ./config_default.yml)
    --dataset NAME         # Optional: Dataset name to use (default: 'latest')
```

## Environment Variables

### `prompt_path`
This variable specifies the path to a prompt file. The file should be a simple text file (`.txt`) or a markdown file (`.md`) containing the desired prompt.
The prompt doesn't have to be the exact chatbot system prompt, it can also be a document that describes the list of policies that should be tested. In this case the chatbot system prompt should be also provided (see [tool chatbot modification](./custom_chatbot.md#Setting-the-system-prompt)).

**Example of prompt file:**
For a complete example of a prompt file, see the [airline chat-agent system prompt](https://github.com/plurai-ai/chatbot_simulator/blob/main/examples/airline/input/wiki.md).

---

### `database_folder`
This variable specifies the path to a folder containing CSV files. Each CSV file represents a database table used by the system and must include at least one row as an example. It is recommended to provide meaningful and indicative names for the columns in each CSV file.

**Example of database_folder:**
For a complete example of a database folder, see the [airline chat-agent database scheme folder](https://github.com/plurai-ai/chatbot_simulator/tree/main/examples/airline/input/data).

The folder should contain CSV files that define your database tables. Here's an example structure from an airline booking system:

**flights.csv**

| flight_number | origin | destination | scheduled_departure_time_est | scheduled_arrival_time_est | dates |
|--------------|---------|-------------|----------------------------|--------------------------|--------|
| HAT001 | PHL | LGA | 06:00:00 | 07:00:00 | {"2024-05-16": {"status": "available", "available_seats": {"basic_economy": 16, "economy": 10, "business": 13}, "prices": {"basic_economy": 87, "economy": 122, "business": 471}}} |

**reservations.csv**

| reservation_id | user_id | origin | destination | flight_type | cabin | flights | passengers | payment_history | created_at | total_baggages | nonfree_baggages | insurance |
|---------------|----------|---------|-------------|-------------|--------|----------|------------|-----------------|------------|----------------|------------------|-----------|
| 4WQ150 | chen_jackson_3290 | DFW | LAX | round_trip | business | [{"origin": "DFW", "destination": "LAX", "flight_number": "HAT170", "date": "2024-05-22"}] | [{"first_name": "Chen", "last_name": "Jackson", "dob": "1956-07-07"}] | [{"payment_id": "gift_card_3576581", "amount": 4986}] | 2024-05-02 03:10:19 | 5 | 0 | no |

**users.csv**

| user_id | name | address | email | dob | payment_methods | saved_passengers | membership | reservations |
|---------|------|---------|-------|-----|-----------------|------------------|------------|--------------|
| mia_li_3668 | {"first_name": "Mia", "last_name": "Li"} | {"address1": "975 Sunset Drive", "city": "Austin", "country": "USA"} | mia.li@example.com | 1990-04-05 | {"credit_card_4421486": {"source": "credit_card", "last_four": "7447"}} | [] | gold | ["NO6JO3"] |


### `tools_file` (optional)
This variable specifies the path to a python script containing all the agent tool functions. 

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
See [airline chat-agent tools python script](https://github.com/plurai-ai/chatbot_simulator/blob/main/examples/airline/input/tools/agent_tools.py) for reference.

---

### `database_validators` (optional)
Data validators are crucial components of the system.  
These functions guide the database generation pipeline, ensuring data integrity and consistency. They are particularly important when dealing with duplicate information across different tables, as they allow for consistency checks.

The `database_validators` variable specifies the path to a Python script that contains the data validation functions.

To define a validation function, use the `@validator` decorator and specify the table to which the function applies.

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

For a complete example of validators in action, see the airline booking system validators at [airline chat-agent database validators python script](https://github.com/plurai-ai/chatbot_simulator/blob/main/examples/airline/input/validators/data_validators.py). This example includes validators for:
- User ID validation (preventing duplicate users)
- Flight ID validation (ensuring unique flight numbers)
- Flight validation (verifying flight details in reservations)
- User validation (maintaining consistency between reservations and user data)
