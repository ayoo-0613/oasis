from collections import Counter
from pathlib import Path
from typing import Any, Optional

from generator.business_simulation.core import (load_archetype_config,
                                                load_schema_config,
                                                validate_generated_agent)
from generator.business_simulation.enrichment import BaseLLMProvider, RoleCardConfig
from generator.business_simulation.run_pipeline import (
    BUSINESS_ARCHETYPE_ROLES,
    OUTPUT_ROLES,
    PIPELINE_CONTEXTUAL_IDENTITY_ROLES,
    run_business_simulation_pipeline,
)


ROOT_DIR = Path(__file__).resolve().parents[2]
ROLES_DIR = ROOT_DIR / "generator" / "business_simulation" / "roles"
BUSINESS_IDEA = "AI-powered website design platform for SMBs."


class RecordingProvider(BaseLLMProvider):
    def __init__(self) -> None:
        self.roles: list[str] = []

    def generate_json(self,
                      prompt: str,
                      system_prompt: Optional[str] = None) -> dict[str, Any]:
        role_line = prompt.splitlines()[0]
        role = role_line.removeprefix("Role: ").strip()
        self.roles.append(role)
        return _role_card_for(role)


def test_pipeline_run_without_contextual_identity_outputs_all_roles():
    payload = run_business_simulation_pipeline(
        business_idea=BUSINESS_IDEA,
        num_consumers=4,
        num_technical_experts=2,
        num_mentors=3,
        consumer_seed=42,
        expert_seed=7,
        mentor_seed=9,
    )

    assert payload["metadata"]["generator"] == "business_simulation.run_pipeline"
    assert payload["metadata"]["contextual_identity_enabled"] is False
    assert list(payload["agents"]) == list(OUTPUT_ROLES)
    assert len(payload["agents"]["consumer"]) == 4
    assert len(payload["agents"]["technical_expert"]) == 2
    assert len(payload["agents"]["mentor"]) == 3
    for role_name in BUSINESS_ARCHETYPE_ROLES:
        assert len(payload["agents"][role_name]) == 3
        assert _archetype_ids(payload, role_name) == _configured_archetype_ids(
            role_name
        )

    _assert_payload_agents_validate(payload)


def test_pipeline_contextual_identity_only_enriches_supported_roles():
    provider = RecordingProvider()

    payload = run_business_simulation_pipeline(
        business_idea=BUSINESS_IDEA,
        num_consumers=2,
        num_technical_experts=2,
        num_mentors=2,
        consumer_seed=42,
        expert_seed=7,
        mentor_seed=9,
        enable_contextual_identity=True,
        role_card_config=RoleCardConfig(enabled=True),
        llm_provider=provider,
    )

    expected_call_counts = {
        "enterprise_buyer": 3,
        "competitor": 3,
        "supplier": 3,
        "technical_expert": 2,
    }
    assert Counter(provider.roles) == expected_call_counts
    assert set(provider.roles) == set(PIPELINE_CONTEXTUAL_IDENTITY_ROLES)

    for role_name in PIPELINE_CONTEXTUAL_IDENTITY_ROLES:
        assert all(
            "contextual_identity" in agent
            for agent in payload["agents"][role_name]
        )
    for role_name in ("consumer", "investor", "regulator", "mentor"):
        assert all(
            "contextual_identity" not in agent
            for agent in payload["agents"][role_name]
        )

    _assert_payload_agents_validate(payload)


def test_pipeline_generation_counts_are_recorded_in_metadata():
    payload = run_business_simulation_pipeline(
        business_idea=BUSINESS_IDEA,
        num_consumers=1,
        num_technical_experts=1,
        num_mentors=1,
        consumer_seed=1,
        expert_seed=2,
        mentor_seed=3,
    )

    assert payload["metadata"]["generation_counts"] == {
        "consumer": 1,
        "enterprise_buyer": 3,
        "competitor": 3,
        "investor": 3,
        "supplier": 3,
        "regulator": 3,
        "technical_expert": 1,
        "mentor": 1,
    }


def _assert_payload_agents_validate(payload: dict[str, Any]) -> None:
    for role_name, agents in payload["agents"].items():
        schema_config = load_schema_config(ROLES_DIR / role_name / "schema_config.json")
        for agent in agents:
            validate_generated_agent(agent, schema_config)


def _archetype_ids(payload: dict[str, Any], role_name: str) -> list[str]:
    return [
        agent["archetype_id"]
        for agent in payload["agents"][role_name]
    ]


def _configured_archetype_ids(role_name: str) -> list[str]:
    archetype_config = load_archetype_config(
        ROLES_DIR / role_name / "archetypes.json"
    )
    return [
        archetype["archetype_id"]
        for archetype in archetype_config["archetypes"]
    ]


def _role_card_for(role: str) -> dict[str, Any]:
    cards = {
        "enterprise_buyer": {
            "market_identity": "Regional SMB marketing agency",
            "organization_type": "Services firm",
            "industry_context": "Small business website delivery",
            "primary_use_case": "Launch client landing pages faster",
            "current_alternative": "Manual design and template editing",
            "key_pain_points": ["Slow drafts", "Repeated customization"],
            "adoption_context": "Pilot for lower-budget client projects",
            "buying_relevance": "Relevant to faster website production",
        },
        "competitor": {
            "market_identity": "No-code website builder incumbent",
            "competitor_type": "Website creation platform",
            "overlap_scope": "SMB landing pages and simple websites",
            "competing_offer": "Drag-and-drop builder with templates",
            "positioning_style": "Ease-of-use and template variety",
            "likely_target_segment": "Small business owners",
            "strategic_posture": "Defend existing SMB workflows",
            "competitive_relevance": "Competes for website creation budgets",
        },
        "supplier": {
            "market_identity": "Cloud hosting and deployment platform",
            "supplier_type": "Infrastructure provider",
            "supplied_capability": "Hosting, deployment, and uptime",
            "dependency_role": "Runs generated business websites",
            "integration_scope": "API-driven deployment workflow",
            "commercial_context": "Usage-based infrastructure spend",
            "supply_relevance": "Required for simple publication flows",
        },
        "technical_expert": {
            "market_identity": "Applied AI web platform architect",
            "expertise_domain": "AI-assisted site generation",
            "technical_scope": "Prompt-to-page generation and deployment",
            "evaluation_lens": "Architecture risk and maintainability",
            "system_concern_focus": ["Template quality", "Deployment safety"],
            "likely_recommendation_style": "Pragmatic risk-based guidance",
            "technical_relevance": "Relevant to product architecture choices",
        },
    }
    return cards[role]

