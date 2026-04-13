from pathlib import Path
from typing import Any, Optional

import pytest

from generator.business_simulation.enrichment import (
    BaseLLMProvider,
    ContextualIdentityError,
    JSONExtractionError,
    RoleCardConfig,
    RoleCardValidationError,
    build_competitor_role_card_prompt,
    build_enterprise_buyer_role_card_prompt,
    enrich_agents_with_contextual_identity,
    extract_json_object,
    load_contextual_identity_enrichment_config,
    validate_contextual_role_card,
)
from generator.business_simulation.roles.consumer import generate_consumer_agents
from generator.business_simulation.roles.enterprise_buyer import (
    generate_enterprise_buyer_agents,
)
from generator.business_simulation.core import (load_schema_config,
                                                validate_generated_agent)


ROOT_DIR = Path(__file__).resolve().parents[2]
ROLES_DIR = ROOT_DIR / "generator" / "business_simulation" / "roles"
BUSINESS_IDEA = (
    "An AI-powered website design product that helps small businesses generate "
    "landing pages and basic business websites from natural language prompts, "
    "with fast editing, template adaptation, and simple deployment."
)


class MockProvider(BaseLLMProvider):
    def __init__(self, payload: dict[str, Any]):
        self.payload = payload
        self.calls: list[tuple[str, Optional[str]]] = []

    def generate_json(self,
                      prompt: str,
                      system_prompt: Optional[str] = None) -> dict[str, Any]:
        self.calls.append((prompt, system_prompt))
        return self.payload


class FailingProvider(BaseLLMProvider):
    def generate_json(self,
                      prompt: str,
                      system_prompt: Optional[str] = None) -> dict[str, Any]:
        raise RuntimeError("provider unavailable")


def test_prompt_builder_includes_schema_and_constraints():
    config = load_schema_config(
        ROLES_DIR / "enterprise_buyer" / "schema_config.json"
    )
    agent = generate_enterprise_buyer_agents(1, config, seed=42)[0]

    prompt = build_enterprise_buyer_role_card_prompt(BUSINESS_IDEA, agent)

    assert BUSINESS_IDEA in prompt
    assert "enterprise_buyer" in prompt
    assert "market_identity" in prompt
    assert "key_pain_points" in prompt
    assert "Do not evaluate the idea" in prompt


def test_competitor_prompt_builder_uses_competitor_schema():
    prompt = build_competitor_role_card_prompt(
        business_idea_description=BUSINESS_IDEA,
        static_agent_profile={"agent_id": "competitor_000001", "role": "competitor"},
    )

    assert "competing_offer" in prompt
    assert "competitive_relevance" in prompt


def test_extract_json_object_from_markdown_fence():
    payload = extract_json_object('```json\n{"market_identity": "SMB builder"}\n```')

    assert payload == {"market_identity": "SMB builder"}


def test_extract_json_object_rejects_malformed_output():
    with pytest.raises(JSONExtractionError):
        extract_json_object("not json")


def test_validate_contextual_role_card_accepts_valid_enterprise_buyer_card():
    card = _enterprise_buyer_card()

    validated = validate_contextual_role_card("enterprise_buyer", card)

    assert validated["market_identity"] == "Regional SMB marketing agency"


def test_validate_contextual_role_card_rejects_missing_required_field():
    card = _enterprise_buyer_card()
    del card["buying_relevance"]

    with pytest.raises(RoleCardValidationError, match="missing fields"):
        validate_contextual_role_card("enterprise_buyer", card)


def test_validate_contextual_role_card_rejects_long_list():
    card = _enterprise_buyer_card()
    card["key_pain_points"] = ["a", "b", "c", "d", "e", "f"]

    with pytest.raises(RoleCardValidationError, match="at most"):
        validate_contextual_role_card(
            "enterprise_buyer",
            card,
            RoleCardConfig(max_list_items=5),
        )


def test_validate_contextual_role_card_coerces_string_list_to_string_field():
    card = {
        "market_identity": "Website builder incumbent",
        "competitor_type": "No-code website platform",
        "overlap_scope": ["SMB landing pages", "Template editing"],
        "competing_offer": "Drag-and-drop website builder",
        "positioning_style": "Ease-of-use and template breadth",
        "likely_target_segment": "Small business owners",
        "strategic_posture": "Defend existing SMB workflows",
        "competitive_relevance": "Competes for simple website creation budgets",
    }

    validated = validate_contextual_role_card("competitor", card)

    assert validated["overlap_scope"] == "SMB landing pages; Template editing"


def test_validate_contextual_role_card_coerces_string_to_string_list_field():
    card = _enterprise_buyer_card()
    card["key_pain_points"] = "Slow first drafts"

    validated = validate_contextual_role_card("enterprise_buyer", card)

    assert validated["key_pain_points"] == ["Slow first drafts"]


def test_enrich_agents_with_contextual_identity_enriches_supported_roles_only():
    buyer_config = load_schema_config(
        ROLES_DIR / "enterprise_buyer" / "schema_config.json"
    )
    consumer_config = load_schema_config(ROLES_DIR / "consumer" / "schema_config.json")
    buyer = generate_enterprise_buyer_agents(1, buyer_config, seed=42)[0]
    consumer = generate_consumer_agents(1, consumer_config, seed=42)[0]
    provider = MockProvider(_enterprise_buyer_card())

    enriched = enrich_agents_with_contextual_identity(
        agents=[buyer, consumer],
        business_idea_description=BUSINESS_IDEA,
        llm_provider=provider,
        role_card_config=RoleCardConfig(enabled=True),
    )

    assert [agent["agent_id"] for agent in enriched] == [
        buyer["agent_id"],
        consumer["agent_id"],
    ]
    assert "contextual_identity" in enriched[0]
    assert "contextual_identity" not in enriched[1]
    assert "contextual_identity" not in buyer
    validate_generated_agent(enriched[0], buyer_config)
    assert len(provider.calls) == 1


def test_enrich_agents_with_contextual_identity_can_skip_provider_errors():
    buyer_config = load_schema_config(
        ROLES_DIR / "enterprise_buyer" / "schema_config.json"
    )
    buyer = generate_enterprise_buyer_agents(1, buyer_config, seed=42)[0]

    with pytest.warns(RuntimeWarning, match="Skipping contextual identity"):
        enriched = enrich_agents_with_contextual_identity(
            agents=[buyer],
            business_idea_description=BUSINESS_IDEA,
            llm_provider=FailingProvider(),
            role_card_config=RoleCardConfig(enabled=True, on_error="skip"),
        )

    assert "contextual_identity" not in enriched[0]


def test_enrich_agents_with_contextual_identity_raises_by_default():
    buyer_config = load_schema_config(
        ROLES_DIR / "enterprise_buyer" / "schema_config.json"
    )
    buyer = generate_enterprise_buyer_agents(1, buyer_config, seed=42)[0]

    with pytest.raises(ContextualIdentityError, match="enrichment failed"):
        enrich_agents_with_contextual_identity(
            agents=[buyer],
            business_idea_description=BUSINESS_IDEA,
            llm_provider=FailingProvider(),
            role_card_config=RoleCardConfig(enabled=True),
        )


def test_load_contextual_identity_enrichment_config_example():
    config = load_contextual_identity_enrichment_config(
        ROOT_DIR
        / "generator"
        / "business_simulation"
        / "enrichment"
        / "contextual_identity_config.example.json"
    )

    assert config.provider.provider_type == "local"
    assert config.provider.model_name == "llama3"
    assert config.role_card.enabled is True


def _enterprise_buyer_card() -> dict[str, Any]:
    return {
        "market_identity": "Regional SMB marketing agency",
        "organization_type": "Services firm serving small businesses",
        "industry_context": "Digital marketing and local business websites",
        "primary_use_case": "Rapid landing page delivery for client campaigns",
        "current_alternative": "Manual designer workflow and template builders",
        "key_pain_points": [
            "Slow first drafts",
            "Repeated template customization",
            "Simple deployment handoffs",
        ],
        "adoption_context": "Would pilot for lower-budget client projects",
        "buying_relevance": "Matches a need for faster website production",
    }
