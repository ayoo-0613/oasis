"""Batch enrichment pipeline for contextual role cards."""

from __future__ import annotations

import logging
import warnings
from typing import Any

from .base import (BaseLLMProvider, ContextualIdentityError, RoleCardConfig)
from .prompts import (CONTEXTUAL_ROLE_CARD_SYSTEM_PROMPT,
                      build_contextual_role_card_prompt)
from .schemas import SUPPORTED_CONTEXTUAL_IDENTITY_ROLES
from .validator import build_role_card_config, validate_contextual_role_card


logger = logging.getLogger(__name__)


def enrich_agents_with_contextual_identity(
    agents: list[dict[str, Any]],
    business_idea_description: str,
    llm_provider: BaseLLMProvider,
    role_card_config: RoleCardConfig | dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Attach contextual role cards to supported-role agents in order."""
    config = build_role_card_config(role_card_config)
    if not config.enabled:
        return [dict(agent) for agent in agents]
    if not business_idea_description.strip():
        raise ContextualIdentityError(
            "business_idea_description is required when contextual identity "
            "enrichment is enabled."
        )

    enriched_agents: list[dict[str, Any]] = []
    for agent in agents:
        role = agent.get("role")
        copied_agent = dict(agent)
        if role not in SUPPORTED_CONTEXTUAL_IDENTITY_ROLES:
            enriched_agents.append(copied_agent)
            continue

        try:
            prompt = build_contextual_role_card_prompt(
                role=role,
                business_idea_description=business_idea_description,
                static_agent_profile=agent,
            )
            logger.info(
                "Generating contextual identity for role=%s provider=%s",
                role,
                llm_provider.__class__.__name__,
            )
            role_card = llm_provider.generate_json(
                prompt=prompt,
                system_prompt=CONTEXTUAL_ROLE_CARD_SYSTEM_PROMPT,
            )
            copied_agent["contextual_identity"] = validate_contextual_role_card(
                role=role,
                role_card=role_card,
                config=config,
            )
        except Exception as exc:
            if config.on_error == "skip":
                warnings.warn(
                    "Skipping contextual identity enrichment for "
                    f"agent_id={agent.get('agent_id')}: {exc}",
                    RuntimeWarning,
                    stacklevel=2,
                )
            else:
                raise ContextualIdentityError(
                    "Contextual identity enrichment failed for "
                    f"agent_id={agent.get('agent_id')}: {exc}"
                ) from exc
        enriched_agents.append(copied_agent)

    return enriched_agents
