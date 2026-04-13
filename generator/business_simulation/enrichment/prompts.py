"""Prompt builders for contextual role-card generation."""

from __future__ import annotations

import json
from typing import Any

from .schemas import (ROLE_CARD_PURPOSES, ROLE_CARD_SCHEMAS,
                      SUPPORTED_CONTEXTUAL_IDENTITY_ROLES)


CONTEXTUAL_ROLE_CARD_SYSTEM_PROMPT = (
    "You generate compact JSON role cards for business simulation agents. "
    "Return strict JSON only. Do not use markdown. Do not evaluate whether "
    "the business idea is good or bad."
)


def build_enterprise_buyer_role_card_prompt(
    business_idea_description: str,
    static_agent_profile: dict[str, Any],
) -> str:
    """Build a prompt for an enterprise buyer contextual role card."""
    return build_contextual_role_card_prompt(
        role="enterprise_buyer",
        business_idea_description=business_idea_description,
        static_agent_profile=static_agent_profile,
    )


def build_competitor_role_card_prompt(
    business_idea_description: str,
    static_agent_profile: dict[str, Any],
) -> str:
    """Build a prompt for a competitor contextual role card."""
    return build_contextual_role_card_prompt(
        role="competitor",
        business_idea_description=business_idea_description,
        static_agent_profile=static_agent_profile,
    )


def build_supplier_role_card_prompt(
    business_idea_description: str,
    static_agent_profile: dict[str, Any],
) -> str:
    """Build a prompt for a supplier contextual role card."""
    return build_contextual_role_card_prompt(
        role="supplier",
        business_idea_description=business_idea_description,
        static_agent_profile=static_agent_profile,
    )


def build_technical_expert_role_card_prompt(
    business_idea_description: str,
    static_agent_profile: dict[str, Any],
) -> str:
    """Build a prompt for a technical expert contextual role card."""
    return build_contextual_role_card_prompt(
        role="technical_expert",
        business_idea_description=business_idea_description,
        static_agent_profile=static_agent_profile,
    )


def build_contextual_role_card_prompt(
    role: str,
    business_idea_description: str,
    static_agent_profile: dict[str, Any],
) -> str:
    """Build a strict JSON prompt for a supported contextual role card."""
    if role not in SUPPORTED_CONTEXTUAL_IDENTITY_ROLES:
        raise ValueError(
            f"Role '{role}' does not support contextual identity prompts."
        )

    schema = ROLE_CARD_SCHEMAS[role]
    schema_payload = {
        field_name: field_type for field_name, field_type in schema.items()
    }
    return "\n".join([
        f"Role: {role}",
        f"Goal: {ROLE_CARD_PURPOSES[role]}",
        "",
        "Business idea description:",
        business_idea_description.strip(),
        "",
        "Static agent profile JSON:",
        json.dumps(static_agent_profile, ensure_ascii=True, sort_keys=True),
        "",
        "Required output JSON schema:",
        json.dumps(schema_payload, ensure_ascii=True, sort_keys=True),
        "",
        "Constraints:",
        "- Instantiate a plausible market-facing identity grounded in the business idea.",
        "- Use the static profile as constraints; do not contradict its structured traits.",
        "- Keep every string concise and concrete.",
        "- Use short lists only where the schema requests list[str].",
        "- Do not evaluate the idea as good, bad, investable, compliant, or feasible.",
        "- Avoid generic filler language and long biographies.",
        "- Return one JSON object only, with exactly the requested fields.",
    ])
