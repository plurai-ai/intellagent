import yaml
from pathlib import Path
import os

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

def get_last_db(base_path = "./results"):
    # Get the last created db in the default result path
    last_dir = get_last_created_directory(base_path)
    if last_dir is None:
        return None
    last_dir = last_dir/'experiments'
    # Get the last created database file in the last created directory
    last_exp = get_last_created_directory(last_dir)
    if os.path.isfile(last_exp / "memory.db"):
        last_db = last_exp / "memory.db"
        return str(last_db)
    return None

def get_latest_dataset(base_path = "./results"):
    # Get the last created db in the default result path
    last_dir = get_last_created_directory(base_path)
    if last_dir is None:
        return None
    last_dir = last_dir/'datasets'
    # Get the last created database file in the last created directory
    last_dataset = get_latest_file(str(last_dir))
    if last_dataset is None:
        return None
    last_dataset = last_dir / last_dataset
    last_dataset, _ = os.path.splitext(last_dataset)
    return last_dataset