import json
import subprocess
import sys
from pathlib import Path

import pytest

from generator.consumer.consumer_generate import (generate_consumer_agents,
                                                  load_schema_config)
from generator.consumer.validator import (validate_distribution,
                                          validate_generated_agent,
                                          validate_schema_config)


ROOT_DIR = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT_DIR / "generator" / "consumer" / "schema_config.json"
SCRIPT_PATH = ROOT_DIR / "generator" / "consumer" / "consumer_generate.py"


def test_schema_config_is_valid():
    config = load_schema_config(CONFIG_PATH)
    validate_schema_config(config)
    assert config["metadata"]["version"] == "2.0.0"
    assert "perceived_behavioral_control" in config["schema"]
    assert config["schema"]["information_search_depth"] == [
        "shallow",
        "moderate",
        "deep",
    ]
    assert config["schema"]["novelty_adoption"] == [
        "innovator",
        "early_adopter",
        "early_majority",
        "late_majority",
        "laggard",
    ]


def test_generate_consumer_agents_is_deterministic():
    config = load_schema_config(CONFIG_PATH)

    first_run = generate_consumer_agents(5, config, seed=42)
    second_run = generate_consumer_agents(5, config, seed=42)
    third_run = generate_consumer_agents(5, config, seed=43)

    assert first_run == second_run
    assert first_run != third_run
    for agent in first_run:
        validate_generated_agent(agent, config)


def test_generate_consumer_agents_output_shape():
    config = load_schema_config(CONFIG_PATH)
    agents = generate_consumer_agents(3, config, seed=7)

    assert [agent["agent_id"] for agent in agents] == [
        "consumer_000001",
        "consumer_000002",
        "consumer_000003",
    ]
    assert all(agent["role"] == "consumer" for agent in agents)
    assert all(
        "perceived_behavioral_control" in agent["behavioral_traits"]
        for agent in agents
    )


def test_v1_labels_do_not_remain_in_v2_schema():
    config = load_schema_config(CONFIG_PATH)

    assert "mainstream" not in config["schema"]["novelty_adoption"]
    assert "balanced" not in config["schema"]["purchase_planning_style"]
    assert "planned" not in config["schema"]["purchase_planning_style"]
    assert config["conditional_ratios"]["perceived_behavioral_control"][
        "parent_field"
    ] == "education_group"


def test_validate_distribution_rejects_invalid_total():
    with pytest.raises(ValueError, match="sum to 1.0"):
        validate_distribution({"low": 0.4, "medium": 0.4, "high": 0.1})


def test_validate_schema_config_rejects_unknown_conditional_value():
    config = load_schema_config(CONFIG_PATH)
    config["conditional_ratios"]["price_sensitivity"]["distributions"]["low"] = {
        "low": 0.1,
        "medium": 0.2,
        "very_high": 0.7,
    }

    with pytest.raises(ValueError, match="legal schema values"):
        validate_schema_config(config)


def test_cli_writes_output(tmp_path):
    output_path = tmp_path / "consumer_agents.json"
    command = [
        sys.executable,
        str(SCRIPT_PATH),
        "--config",
        str(CONFIG_PATH),
        "--num_agents",
        "2",
        "--seed",
        "42",
        "--output",
        str(output_path),
        "--pretty",
    ]

    subprocess.run(command, check=True, cwd=ROOT_DIR)

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert len(payload) == 2
    assert payload[0]["agent_id"] == "consumer_000001"
