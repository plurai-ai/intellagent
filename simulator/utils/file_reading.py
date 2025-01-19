import yaml
from pathlib import Path
import os
import importlib.util
import inspect


def get_latest_file(directory_path, extension='pickle') -> str:
    """
    Get the most recently modified file in a directory with a specific extension
    :param directory_path:
    :param extension:
    :return: The most recently modified file
    """
    # Convert the directory path to a Path object
    directory_path = Path(directory_path)

    # Get a list of all the files in the directory with the extension
    json_files = [f for f in directory_path.glob(f"*.{extension}") if f.is_file()]

    # Find the most recently modified JSON file
    latest_file = max(json_files, key=lambda f: f.stat().st_mtime, default=None)
    if latest_file is None:
        return None
    return latest_file.name


def validator(table=None):
    def decorator(func):
        func.is_collected = True  # Add a custom attribute to the function
        func.table = table  # Add a category or variable to the function
        return func

    return decorator


def get_validators_from_module(file_path, table_name):
    """
    Get a validators from a module in a file
    :param file_path:
    :param table_name: The table name
    :return: the list of the table validators
    """
    if not os.path.isfile(file_path):
        return []  # Validator is optional

    # Load the module dynamically
    module_name = os.path.splitext(os.path.basename(file_path))[0]
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    collected = []
    for name, obj in inspect.getmembers(module, inspect.isfunction):
        if getattr(obj, "is_collected", False) and obj.table == table_name:
            collected.append(obj)
    return collected


def update_dict_keys_if_exists(dict1, dict2):
    """
    Update the keys of dict1 with the values from dict2 only if the keys exist in dict2.

    Args:
        dict1 (dict): The first dictionary to be updated.
        dict2 (dict): The second dictionary providing update values.
    """
    for key in dict1.keys():
        if key in dict2:
            dict1[key] = dict2[key]


def override_llm(config, llm_config):
    """
    Override all the LLMs configuration with the new LLM type
    :param config: The configuration dictionary
    :param llm_config: The override configuration dictionary
    """
    update_dict_keys_if_exists(config['environment']['task_description']['llm'], llm_config)
    update_dict_keys_if_exists(config['description_generator']['llm_policy'], llm_config)
    update_dict_keys_if_exists(config['description_generator']['llm_edge'], llm_config)
    update_dict_keys_if_exists(config['description_generator']['llm_description'], llm_config)
    update_dict_keys_if_exists(config['description_generator']['llm_refinement'], llm_config)
    update_dict_keys_if_exists(config['event_generator']['event_graph']['llm'], llm_config)
    update_dict_keys_if_exists(config['dialog_manager']['critique_config']['llm'], llm_config)
    update_dict_keys_if_exists(config['dialog_manager']['llm_user'], llm_config)
    update_dict_keys_if_exists(config['analysis']['llm'], llm_config)
    return config


def override_config(override_config_file, config_file='config/config_default.yml'):
    """
    Override the default configuration file with the override configuration file
    :param config_file: The default configuration file
    :param override_config_file: The override configuration file
    """

    def override_dict(config_dict, override_config_dict):
        for key, value in override_config_dict.items():
            if isinstance(value, dict):
                if key not in config_dict:
                    config_dict[key] = value
                else:
                    override_dict(config_dict[key], value)
            else:
                config_dict[key] = value
        return config_dict

    with open(config_file, 'r') as file:
        default_config_dict = yaml.safe_load(file)
    with open(override_config_file, 'r') as file:
        override_config_dict = yaml.safe_load(file)
    config_dict = override_dict(default_config_dict, override_config_dict)
    if 'llm_intellagent' in config_dict:
        override_llm(config_dict, config_dict['llm_intellagent'])
    if 'llm_chat' in config_dict:
        update_dict_keys_if_exists(config_dict['dialog_manager']['llm_chat'], config_dict['llm_chat'])
    return config_dict


def get_last_created_directory(path):
    # Convert path to Path object for convenience
    if not os.path.isdir(path):
        return None
    path = Path(path)

    # Get all directories in the specified path
    directories = [d for d in path.iterdir() if d.is_dir()]

    # Sort directories by creation time (newest first) and get the first one
    last_created_dir = max(directories, key=lambda d: d.stat().st_ctime, default=None)

    return last_created_dir


def get_last_db(base_path="./results"):
    # Get the last created db in the default result path
    last_dir = get_last_created_directory(base_path)
    if last_dir is None:
        return None
    last_dir = last_dir / 'experiments'
    # Get the last created database file in the last created directory
    last_exp = get_last_created_directory(last_dir)
    try:
        if os.path.isfile(last_exp / "memory.db"):
            last_db = last_exp / "memory.db"
            return str(last_db)
    except:
        pass
    return None


def get_latest_dataset(base_path="./results"):
    # Get the last created db in the default result path
    last_dir = get_last_created_directory(base_path)
    if last_dir is None:
        return None
    last_dir = last_dir / 'datasets'
    # Get the last created database file in the last created directory
    last_dataset = get_latest_file(str(last_dir))
    if last_dataset is None:
        return None
    last_dataset = last_dir / last_dataset
    last_dataset, _ = os.path.splitext(last_dataset)
    return last_dataset