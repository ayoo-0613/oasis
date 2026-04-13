import json
import importlib
import subprocess
import sys
from pathlib import Path

import pytest

from generator.business_simulation.core import (load_schema_config,
                                                resolve_role_definition,
                                                validate_distribution,
                                                validate_generated_agent,
                                                validate_schema_config)
from generator.business_simulation.roles.competitor import (
    generate_competitor_agents,)
from generator.business_simulation.roles.consumer import (
    generate_consumer_agents,)
from generator.business_simulation.roles.enterprise_buyer import (
    generate_enterprise_buyer_agents,)
from generator.business_simulation.roles.investor import (
    generate_investor_agents,)
from generator.business_simulation.roles.mentor import generate_mentor_agents
from generator.business_simulation.roles.regulator import (
    generate_regulator_agents,)
from generator.business_simulation.roles.supplier import (
    generate_supplier_agents,)
from generator.business_simulation.roles.technical_expert import (
    generate_technical_expert_agents,)


ROOT_DIR = Path(__file__).resolve().parents[2]
GENERATOR_DIR = ROOT_DIR / "generator" / "business_simulation" / "roles"
ROLE_CASES = {
    "consumer": {
        "config": GENERATOR_DIR / "consumer" / "schema_config.json",
        "script": GENERATOR_DIR / "consumer" / "generate.py",
        "generator": generate_consumer_agents,
        "expected_groups": [
            "demographic",
            "behavioral_traits",
            "consumption_preferences",
        ],
    },
    "enterprise_buyer": {
        "config": GENERATOR_DIR / "enterprise_buyer" / "schema_config.json",
        "script": GENERATOR_DIR / "enterprise_buyer" / "generate.py",
        "generator": generate_enterprise_buyer_agents,
        "expected_groups": [
            "organization_profile",
            "buying_capabilities",
            "procurement_preferences",
        ],
    },
    "competitor": {
        "config": GENERATOR_DIR / "competitor" / "schema_config.json",
        "script": GENERATOR_DIR / "competitor" / "generate.py",
        "generator": generate_competitor_agents,
        "expected_groups": [
            "firm_profile",
            "strategic_capabilities",
            "competitive_behavior",
        ],
    },
    "investor": {
        "config": GENERATOR_DIR / "investor" / "schema_config.json",
        "script": GENERATOR_DIR / "investor" / "generate.py",
        "generator": generate_investor_agents,
        "expected_groups": [
            "fund_profile",
            "investment_preferences",
            "evaluation_style",
        ],
    },
    "supplier": {
        "config": GENERATOR_DIR / "supplier" / "schema_config.json",
        "script": GENERATOR_DIR / "supplier" / "generate.py",
        "generator": generate_supplier_agents,
        "expected_groups": [
            "supply_profile",
            "commercial_capabilities",
            "partnership_preferences",
        ],
    },
    "regulator": {
        "config": GENERATOR_DIR / "regulator" / "schema_config.json",
        "script": GENERATOR_DIR / "regulator" / "generate.py",
        "generator": generate_regulator_agents,
        "expected_groups": [
            "regulatory_profile",
            "oversight_posture",
            "review_priorities",
        ],
    },
    "technical_expert": {
        "config": GENERATOR_DIR / "technical_expert" / "schema_config.json",
        "script": GENERATOR_DIR / "technical_expert" / "generate.py",
        "generator": generate_technical_expert_agents,
        "expected_groups": [
            "expertise_profile",
            "technical_capabilities",
            "assessment_style",
        ],
    },
    "mentor": {
        "config": GENERATOR_DIR / "mentor" / "schema_config.json",
        "script": GENERATOR_DIR / "mentor" / "generate.py",
        "generator": generate_mentor_agents,
        "expected_groups": [
            "mentor_profile",
            "advisory_style",
            "strategic_focus",
        ],
    },
}


def test_consumer_schema_config_is_valid():
    config = load_schema_config(ROLE_CASES["consumer"]["config"])
    validate_schema_config(config)
    assert config["metadata"]["version"] == "2.0.0"
    assert config["metadata"]["role"] == "consumer"
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
    config = load_schema_config(ROLE_CASES["consumer"]["config"])

    first_run = generate_consumer_agents(5, config, seed=42)
    second_run = generate_consumer_agents(5, config, seed=42)
    third_run = generate_consumer_agents(5, config, seed=43)

    assert first_run == second_run
    assert first_run != third_run
    for agent in first_run:
        validate_generated_agent(agent, config)


def test_generate_consumer_agents_output_shape():
    config = load_schema_config(ROLE_CASES["consumer"]["config"])
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
    config = load_schema_config(ROLE_CASES["consumer"]["config"])

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
    config = load_schema_config(ROLE_CASES["consumer"]["config"])
    config["conditional_ratios"]["price_sensitivity"]["distributions"]["low"] = {
        "low": 0.1,
        "medium": 0.2,
        "very_high": 0.7,
    }

    with pytest.raises(ValueError, match="legal schema values"):
        validate_schema_config(config)


@pytest.mark.parametrize(
    ("role_name", "expected_first_field"),
    [
        ("consumer", "age_group"),
        ("enterprise_buyer", "company_size"),
        ("competitor", "firm_size"),
        ("investor", "fund_type"),
        ("supplier", "supplier_type"),
        ("regulator", "jurisdiction_level"),
        ("technical_expert", "domain_specialization"),
        ("mentor", "career_stage"),
    ],
)
def test_generate_agents_for_each_role(role_name, expected_first_field):
    role_case = ROLE_CASES[role_name]
    config = load_schema_config(role_case["config"])
    agents = role_case["generator"](4, config, seed=11)
    role_definition = resolve_role_definition(config)

    assert [agent["agent_id"] for agent in agents] == [
        f"{role_definition.agent_id_prefix}_000001",
        f"{role_definition.agent_id_prefix}_000002",
        f"{role_definition.agent_id_prefix}_000003",
        f"{role_definition.agent_id_prefix}_000004",
    ]
    assert all(agent["role"] == role_name for agent in agents)
    assert all(
        expected_first_field in agent[role_definition.output_groups[0]]
        for agent in agents
    )

    for agent in agents:
        validate_generated_agent(agent, config)


@pytest.mark.parametrize(
    "role_name",
    [
        "enterprise_buyer",
        "competitor",
        "investor",
        "supplier",
        "regulator",
        "technical_expert",
        "mentor",
    ],
)
def test_role_schema_configs_are_valid(role_name):
    role_case = ROLE_CASES[role_name]
    config = load_schema_config(role_case["config"])
    role_definition = resolve_role_definition(config)

    validate_schema_config(config)
    assert config["metadata"]["role"] == role_name
    assert list(role_definition.output_groups) == role_case["expected_groups"]
    assert config["metadata"]["enrichment"]["enabled_by_default"] is False


@pytest.mark.parametrize(
    "role_name",
    [
        "consumer",
        "enterprise_buyer",
        "competitor",
        "investor",
        "supplier",
        "regulator",
        "technical_expert",
        "mentor",
    ],
)
def test_cli_writes_output(tmp_path, role_name):
    role_case = ROLE_CASES[role_name]
    output_path = tmp_path / "consumer_agents.json"
    command = [
        sys.executable,
        str(role_case["script"]),
        "--config",
        str(role_case["config"]),
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
    assert payload[0]["agent_id"].startswith(f"{role_name}_")


def test_validate_schema_config_rejects_mismatched_output_groups():
    config = load_schema_config(ROLE_CASES["competitor"]["config"])
    config["metadata"]["output_groups"] = [
        "firm_profile",
        "strategic_capabilities",
    ]

    with pytest.raises(ValueError, match="output groups"):
        validate_schema_config(config)


def test_validate_generated_agent_rejects_unknown_top_level_key():
    config = load_schema_config(ROLE_CASES["enterprise_buyer"]["config"])
    agent = generate_enterprise_buyer_agents(1, config, seed=5)[0]
    agent["free_text_persona"] = "should not be here"

    with pytest.raises(ValueError, match="unsupported top-level keys"):
        validate_generated_agent(agent, config)


def test_legacy_consumer_imports_remain_available():
    legacy_module = importlib.import_module("generator.consumer.consumer_generate")
    legacy_validator = importlib.import_module("generator.consumer.validator")

    assert hasattr(legacy_module, "generate_consumer_agents")
    assert hasattr(legacy_module, "load_schema_config")
    assert hasattr(legacy_validator, "validate_schema_config")


def test_investor_schema_contains_market_and_valuation_controls():
    config = load_schema_config(ROLE_CASES["investor"]["config"])

    assert "market_size_preference" in config["schema"]
    assert "valuation_sensitivity" in config["schema"]
    assert config["conditional_ratios"]["team_risk_tolerance"][
        "parent_field"
    ] == "stage_focus"


def test_supplier_schema_contains_negotiation_and_capacity_controls():
    config = load_schema_config(ROLE_CASES["supplier"]["config"])

    assert "volume_commitment_requirement" in config["schema"]
    assert "negotiation_rigidity" in config["schema"]
    assert config["conditional_ratios"]["supply_resilience"][
        "parent_field"
    ] == "capacity_flexibility"


def test_regulator_schema_contains_compliance_and_policy_controls():
    config = load_schema_config(ROLE_CASES["regulator"]["config"])

    assert "evidence_burden" in config["schema"]
    assert "cross_border_sensitivity" in config["schema"]
    assert config["conditional_ratios"]["review_strictness"][
        "parent_field"
    ] == "public_risk_focus"


def test_technical_expert_schema_contains_architecture_and_debt_controls():
    config = load_schema_config(ROLE_CASES["technical_expert"]["config"])

    assert "architecture_risk_sensitivity" in config["schema"]
    assert "technical_debt_sensitivity" in config["schema"]
    assert config["conditional_ratios"]["review_depth"][
        "parent_field"
    ] == "evidence_standard"


def test_mentor_schema_contains_strategy_and_experience_controls():
    config = load_schema_config(ROLE_CASES["mentor"]["config"])

    assert "market_expansion_focus" in config["schema"]
    assert "capital_efficiency_focus" in config["schema"]
    assert config["conditional_ratios"]["org_design_focus"][
        "parent_field"
    ] == "company_building_experience"
