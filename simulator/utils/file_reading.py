import yaml
from pathlib import Path


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
