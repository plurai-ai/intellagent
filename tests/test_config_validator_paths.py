"""Regression guard against the validators-path bug where config files reference
a non-existent file (e.g. validators.py instead of data_validators.py), causing
get_validators_from_module() to silently return [] and validators to never run.
"""

import glob
import os
import yaml
import pytest

CONFIG_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'config',
)


def _shipped_configs_with_validator_paths():
    """Yield (config_name, validator_path) for every shipped config that sets
    a non-empty database_validators path."""
    for path in sorted(glob.glob(os.path.join(CONFIG_DIR, 'config_*.yml'))):
        with open(path) as f:
            cfg = yaml.safe_load(f) or {}
        env = cfg.get('environment') or {}
        validator_path = env.get('database_validators')
        if validator_path:
            yield os.path.basename(path), validator_path


@pytest.mark.parametrize(
    'config_name,validator_path',
    list(_shipped_configs_with_validator_paths()),
)
def test_shipped_config_validator_path_exists(config_name, validator_path):
    """Every shipped config_*.yml that sets a non-empty database_validators
    path must point to a file that actually exists."""
    assert os.path.isfile(validator_path), (
        f"{config_name}: database_validators points to '{validator_path}' "
        f"but that file does not exist. The framework's get_validators_from_module() "
        f"silently returns [] in this case, so validators never run."
    )


def test_airline_validators_actually_load():
    """End-to-end check: with the fixed path, all 4 airline validators load."""
    from simulator.utils.file_reading import get_validators_from_module
    path = './examples/airline/input/validators/data_validators.py'
    tables_with_validators = ['users', 'flights', 'reservations']
    for table in tables_with_validators:
        validators = get_validators_from_module(path, table)
        assert validators, f"airline {table} table has no validators loaded from {path}"


def test_retail_validators_actually_load():
    """End-to-end check: with the fixed path, retail validators load."""
    from simulator.utils.file_reading import get_validators_from_module
    path = './examples/retail/input/validators/data_validators.py'
    validators_found = False
    for table in ['users', 'orders', 'products']:
        if get_validators_from_module(path, table):
            validators_found = True
            break
    assert validators_found, (
        f"No validators found for any retail table in {path}. "
        f"Either the path is wrong or no @validator-decorated functions exist."
    )
