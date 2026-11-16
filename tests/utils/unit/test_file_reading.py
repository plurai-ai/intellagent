import os
from pathlib import Path

import pytest
from textwrap import dedent

import yaml

from simulator.utils.file_reading import (
    get_last_created_directory,
    get_last_db,
    get_latest_dataset,
    get_latest_file,
    get_validators_from_module,
    override_config,
    override_llm,
    update_dict_keys_if_exists,
    validator,
)


def test_get_latest_file_returns_newest_matching_file(tmp_path):
    """When a directory has multiple matching files, then the newest matching file name is returned."""
    old_file = tmp_path / "older.pickle"
    new_file = tmp_path / "newer.pickle"
    old_file.write_text("old")
    new_file.write_text("new")
    os.utime(old_file, (1, 1))
    os.utime(new_file, (2, 2))

    result = get_latest_file(tmp_path)

    assert result == "newer.pickle"


def test_get_latest_file_returns_none_when_no_matching_files_exist(tmp_path):
    """When no files match the requested extension, then the helper returns None instead of raising."""
    (tmp_path / "notes.txt").write_text("irrelevant")

    result = get_latest_file(tmp_path, extension="pickle")

    assert result is None


def test_get_latest_file_honors_custom_extension(tmp_path):
    """When a custom extension is requested, then only matching files are considered for the latest result."""
    old_file = tmp_path / "older.csv"
    new_file = tmp_path / "newer.csv"
    ignored_file = tmp_path / "ignored.pickle"
    old_file.write_text("old")
    new_file.write_text("new")
    ignored_file.write_text("ignore")
    os.utime(old_file, (1, 1))
    os.utime(new_file, (2, 2))

    result = get_latest_file(tmp_path, extension="csv")

    assert result == "newer.csv"


def test_validator_decorator_marks_function_with_collection_metadata():
    """When a validator is decorated, then it carries the table and collection markers used by discovery."""

    @validator(table="users")
    def validate_users(df, dataset):
        return df, dataset

    assert validate_users.is_collected is True
    assert validate_users.table == "users"


def test_get_validators_from_module_returns_only_matching_validators(tmp_path):
    """When a module exports multiple validators, then only the ones for the requested table are collected."""
    module_path = tmp_path / "validators.py"
    module_path.write_text(
        dedent(
            """
            from simulator.utils.file_reading import validator

            @validator(table="users")
            def users_validator(df, dataset):
                return df, dataset

            @validator(table="orders")
            def orders_validator(df, dataset):
                return df, dataset

            def plain_function(df, dataset):
                return df, dataset
            """
        )
    )

    validators = get_validators_from_module(str(module_path), "users")

    assert len(validators) == 1
    assert validators[0].__name__ == "users_validator"


def test_get_validators_from_module_returns_empty_list_for_missing_module(tmp_path):
    """When the validator module path does not exist, then discovery should fail closed with an empty list."""
    missing_module = tmp_path / "missing_validators.py"

    validators = get_validators_from_module(str(missing_module), "users")

    assert validators == []


def test_update_dict_keys_if_exists_only_updates_preexisting_keys():
    """When overriding a dictionary, then only keys already present in the target are updated."""
    target = {"keep": 1, "change": 2}
    source = {"change": 20, "new": 30}

    update_dict_keys_if_exists(target, source)

    assert target == {"keep": 1, "change": 20}


def test_override_llm_updates_all_supported_nested_sections():
    """When an llm override is applied, then every supported nested config section receives updated existing keys only."""
    config = {
        "environment": {"task_description": {"llm": {"type": "openai", "name": "base"}}},
        "description_generator": {
            "llm_policy": {"type": "openai", "name": "base", "temperature": 0.0},
            "llm_edge": {"type": "openai", "name": "base", "temperature": 0.0},
            "llm_description": {"type": "openai", "name": "base", "temperature": 0.0},
            "llm_refinement": {"type": "openai", "name": "base", "temperature": 0.0},
        },
        "event_generator": {"event_graph": {"llm": {"type": "openai", "name": "base", "temperature": 0.0}}},
        "dialog_manager": {
            "critique_config": {"llm": {"type": "openai", "name": "base", "temperature": 0.0}},
            "llm_user": {"type": "openai", "name": "base", "temperature": 0.0},
        },
        "analysis": {"llm": {"type": "openai", "name": "base", "temperature": 0.0}},
    }
    llm_override = {"type": "azure", "name": "new-model", "temperature": 0.25}

    result = override_llm(config, llm_override)

    assert result["environment"]["task_description"]["llm"]["type"] == "azure"
    assert result["description_generator"]["llm_policy"]["name"] == "new-model"
    assert result["description_generator"]["llm_edge"]["temperature"] == 0.25
    assert result["description_generator"]["llm_description"]["type"] == "azure"
    assert result["description_generator"]["llm_refinement"]["name"] == "new-model"
    assert result["event_generator"]["event_graph"]["llm"]["name"] == "new-model"
    assert result["dialog_manager"]["critique_config"]["llm"]["type"] == "azure"
    assert result["dialog_manager"]["llm_user"]["temperature"] == 0.25
    assert result["analysis"]["llm"]["name"] == "new-model"


def test_override_config_deep_merges_yaml_and_applies_llm_overrides(tmp_path):
    """When an override file is loaded, then nested keys are merged and llm shortcuts are applied consistently."""
    default_config = {
        "environment": {"task_description": {"llm": {"type": "openai", "name": "base-task"}}},
        "description_generator": {
            "llm_policy": {"type": "openai", "name": "base-policy"},
            "llm_edge": {"type": "openai", "name": "base-edge"},
            "llm_description": {"type": "openai", "name": "base-desc"},
            "llm_refinement": {"type": "openai", "name": "base-refine"},
        },
        "event_generator": {"event_graph": {"llm": {"type": "openai", "name": "base-event"}}},
        "dialog_manager": {
            "critique_config": {"llm": {"type": "openai", "name": "base-critique"}},
            "llm_user": {"type": "openai", "name": "base-user"},
            "llm_chat": {"type": "openai", "name": "base-chat"},
        },
        "analysis": {"llm": {"type": "openai", "name": "base-analysis"}},
        "keep_section": {"nested": {"value": 1}},
    }
    override_config_data = {
        "environment": {"task_description": {"content": "kept"}},
        "keep_section": {"nested": {"value": 2, "new_value": 3}},
        "llm_intellagent": {"type": "azure", "name": "override-all", "temperature": 0.1},
        "llm_chat": {"type": "anthropic", "name": "chat-override"},
    }
    default_path = tmp_path / "default.yml"
    override_path = tmp_path / "override.yml"
    default_path.write_text(yaml.safe_dump(default_config))
    override_path.write_text(yaml.safe_dump(override_config_data))

    result = override_config(str(override_path), config_file=str(default_path))

    assert result["environment"]["task_description"]["content"] == "kept"
    assert result["keep_section"]["nested"] == {"value": 2, "new_value": 3}
    assert result["environment"]["task_description"]["llm"]["type"] == "azure"
    assert result["description_generator"]["llm_policy"]["name"] == "override-all"
    assert result["event_generator"]["event_graph"]["llm"]["type"] == "azure"
    assert result["dialog_manager"]["llm_chat"]["name"] == "chat-override"


def _set_directory_ctimes(monkeypatch, timestamps):
    """Keep real filesystem metadata, but make the ordering under test explicit."""
    real_stat = Path.stat

    def stat_with_ctime(path, *args, **kwargs):
        result = real_stat(path, *args, **kwargs)
        if path in timestamps:
            fields = list(result)
            fields[9] = timestamps[path]  # st_ctime, not the settable st_mtime
            return os.stat_result(fields)
        return result

    monkeypatch.setattr(Path, "stat", stat_with_ctime)


@pytest.mark.parametrize("newest_name", ["older", "newer"])
def test_get_last_created_directory_returns_newest_directory(tmp_path, monkeypatch, newest_name):
    """The largest st_ctime wins, independently of names and creation order."""
    older_dir = tmp_path / "older"
    newer_dir = tmp_path / "newer"
    older_dir.mkdir()
    newer_dir.mkdir()

    newest_dir = tmp_path / newest_name
    _set_directory_ctimes(monkeypatch, {
        older_dir: 20 if newest_dir == older_dir else 10,
        newer_dir: 20 if newest_dir == newer_dir else 10,
    })

    result = get_last_created_directory(tmp_path)

    assert result == newest_dir


def test_get_last_created_directory_returns_none_for_missing_path(tmp_path):
    """When the base path does not exist, then the helper should return None without raising."""
    missing_path = tmp_path / "missing"

    result = get_last_created_directory(missing_path)

    assert result is None


@pytest.mark.parametrize("newest_name", ["older", "newer"])
def test_get_last_db_returns_latest_memory_db_path(tmp_path, monkeypatch, newest_name):
    """Select the database below the results directory with the largest st_ctime."""
    results_dir = tmp_path / "results"
    older_exp = results_dir / "older" / "experiments" / "run-a"
    newer_exp = results_dir / "newer" / "experiments" / "run-b"
    older_exp.mkdir(parents=True)
    newer_exp.mkdir(parents=True)
    (older_exp / "memory.db").write_text("old")
    (newer_exp / "memory.db").write_text("new")

    newest_exp = older_exp if newest_name == "older" else newer_exp
    _set_directory_ctimes(monkeypatch, {
        results_dir / "older": 20 if newest_name == "older" else 10,
        results_dir / "newer": 20 if newest_name == "newer" else 10,
    })

    result = get_last_db(str(results_dir))

    assert result == str(newest_exp / "memory.db")


def test_get_last_db_returns_none_when_memory_db_is_missing(tmp_path):
    """When the newest experiment has no database file, then the helper returns None instead of failing."""
    results_dir = tmp_path / "results"
    exp_dir = results_dir / "only" / "experiments" / "run-a"
    exp_dir.mkdir(parents=True)

    result = get_last_db(str(results_dir))

    assert result is None


def test_get_latest_dataset_returns_dataset_path_without_extension(tmp_path):
    """When datasets exist, then the helper returns the newest dataset path without its file extension."""
    results_dir = tmp_path / "results"
    datasets_dir = results_dir / "latest" / "datasets"
    datasets_dir.mkdir(parents=True)
    first_dataset = datasets_dir / "dataset_a.pickle"
    second_dataset = datasets_dir / "dataset_b.pickle"
    first_dataset.write_text("old")
    second_dataset.write_text("new")
    os.utime(first_dataset, (1, 1))
    os.utime(second_dataset, (2, 2))

    result = get_latest_dataset(str(results_dir))

    assert result == str(datasets_dir / "dataset_b")


def test_get_latest_dataset_returns_none_when_no_dataset_exists(tmp_path):
    """When the dataset folder is absent or empty, then the helper returns None safely."""
    results_dir = tmp_path / "results"
    (results_dir / "latest").mkdir(parents=True)

    result = get_latest_dataset(str(results_dir))

    assert result is None
