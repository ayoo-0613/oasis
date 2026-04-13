"""Role-card schemas for scenario-conditioned contextual identities."""

from __future__ import annotations


SUPPORTED_CONTEXTUAL_IDENTITY_ROLES = frozenset({
    "enterprise_buyer",
    "competitor",
    "supplier",
    "technical_expert",
})

ROLE_CARD_SCHEMAS: dict[str, dict[str, str]] = {
    "enterprise_buyer": {
        "market_identity": "str",
        "organization_type": "str",
        "industry_context": "str",
        "primary_use_case": "str",
        "current_alternative": "str",
        "key_pain_points": "list[str]",
        "adoption_context": "str",
        "buying_relevance": "str",
    },
    "competitor": {
        "market_identity": "str",
        "competitor_type": "str",
        "overlap_scope": "str",
        "competing_offer": "str",
        "positioning_style": "str",
        "likely_target_segment": "str",
        "strategic_posture": "str",
        "competitive_relevance": "str",
    },
    "supplier": {
        "market_identity": "str",
        "supplier_type": "str",
        "supplied_capability": "str",
        "dependency_role": "str",
        "integration_scope": "str",
        "commercial_context": "str",
        "supply_relevance": "str",
    },
    "technical_expert": {
        "market_identity": "str",
        "expertise_domain": "str",
        "technical_scope": "str",
        "evaluation_lens": "str",
        "system_concern_focus": "list[str]",
        "likely_recommendation_style": "str",
        "technical_relevance": "str",
    },
}

ROLE_CARD_PURPOSES: dict[str, str] = {
    "enterprise_buyer": (
        "Instantiate a plausible organization-level buyer that could consider "
        "the idea in this market scenario."
    ),
    "competitor": (
        "Instantiate a plausible competing company, product, or alternative "
        "provider archetype in this market scenario."
    ),
    "supplier": (
        "Instantiate a plausible upstream provider, infrastructure vendor, or "
        "enabling partner relevant to this business scenario."
    ),
    "technical_expert": (
        "Instantiate a plausible technical expert identity relevant to the "
        "business idea and its likely technical stack."
    ),
}


def get_role_card_schema(role: str) -> dict[str, str]:
    """Return the contextual role-card schema for a supported role."""
    return ROLE_CARD_SCHEMAS[role]
