"""JSON config loading for contextual identity enrichment."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .base import LLMProviderConfig, RoleCardConfig


@dataclass(frozen=True)
class ContextualIdentityEnrichmentConfig:
    """Combined provider and role-card enrichment configuration."""

    provider: LLMProviderConfig
    role_card: RoleCardConfig


def load_contextual_identity_enrichment_config(
    config_path: str | Path,
) -> ContextualIdentityEnrichmentConfig:
    """Load contextual identity enrichment config from JSON.

    YAML is intentionally not supported here because the project currently uses
    JSON configs and this feature should not add dependencies.
    """
    with Path(config_path).open("r", encoding="utf-8") as config_file:
        payload = json.load(config_file)
    if not isinstance(payload, dict):
        raise ValueError("Contextual identity config must be a JSON object.")

    provider_payload = payload.get("provider", payload)
    role_card_payload = payload.get("role_card", payload)
    if not isinstance(provider_payload, dict):
        raise ValueError("Contextual identity provider config must be an object.")
    if not isinstance(role_card_payload, dict):
        raise ValueError("Contextual identity role_card config must be an object.")

    return ContextualIdentityEnrichmentConfig(
        provider=LLMProviderConfig(**_filter_config_fields(
            provider_payload,
            LLMProviderConfig,
        )),
        role_card=RoleCardConfig(**_filter_config_fields(
            role_card_payload,
            RoleCardConfig,
        )),
    )


def _filter_config_fields(payload: dict[str, Any], config_type: type) -> dict[str, Any]:
    valid_fields = set(config_type.__dataclass_fields__)  # type: ignore[attr-defined]
    return {
        key: value for key, value in payload.items()
        if key in valid_fields
    }
