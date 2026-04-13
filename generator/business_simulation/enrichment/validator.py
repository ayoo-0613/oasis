"""Validation for contextual role cards."""

from __future__ import annotations

from typing import Any

from .base import RoleCardConfig, RoleCardValidationError
from .schemas import ROLE_CARD_SCHEMAS, SUPPORTED_CONTEXTUAL_IDENTITY_ROLES


def build_role_card_config(config: RoleCardConfig | dict[str, Any] | None
                           ) -> RoleCardConfig:
    """Normalize role-card config from a dataclass, dict, or None."""
    if config is None:
        return RoleCardConfig()
    if isinstance(config, RoleCardConfig):
        return config
    return RoleCardConfig(**config)


def validate_contextual_role_card(
    role: str,
    role_card: dict[str, Any],
    config: RoleCardConfig | dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate and return a normalized contextual role card."""
    role_card_config = build_role_card_config(config)
    if role not in SUPPORTED_CONTEXTUAL_IDENTITY_ROLES:
        raise RoleCardValidationError(
            f"Role '{role}' does not support contextual identity enrichment."
        )
    if not isinstance(role_card, dict):
        raise RoleCardValidationError("Contextual role card must be an object.")

    schema = ROLE_CARD_SCHEMAS[role]
    expected_fields = set(schema)
    actual_fields = set(role_card)
    missing_fields = sorted(expected_fields.difference(actual_fields))
    if missing_fields:
        raise RoleCardValidationError(
            f"Contextual role card for '{role}' missing fields: "
            f"{missing_fields}."
        )

    extra_fields = sorted(actual_fields.difference(expected_fields))
    if role_card_config.strict_validation and extra_fields:
        raise RoleCardValidationError(
            f"Contextual role card for '{role}' has unexpected fields: "
            f"{extra_fields}."
        )

    normalized: dict[str, Any] = {}
    for field_name, field_type in schema.items():
        value = role_card[field_name]
        if value is None:
            raise RoleCardValidationError(
                f"Contextual role card field '{field_name}' must not be null."
            )
        if field_type == "str":
            normalized[field_name] = _validate_short_string(
                value=value,
                field_name=field_name,
                max_field_length=role_card_config.max_field_length,
                max_items=role_card_config.max_list_items,
            )
            continue
        if field_type == "list[str]":
            normalized[field_name] = _validate_short_string_list(
                value=value,
                field_name=field_name,
                max_items=role_card_config.max_list_items,
                max_field_length=role_card_config.max_field_length,
            )
            continue
        raise RoleCardValidationError(
            f"Unsupported contextual role-card field type '{field_type}'."
        )

    return normalized


def _validate_short_string(*,
                           value: Any,
                           field_name: str,
                           max_field_length: int,
                           max_items: int) -> str:
    if isinstance(value, list):
        string_items = _validate_short_string_list(
            value=value,
            field_name=field_name,
            max_items=max_items,
            max_field_length=max_field_length,
        )
        value = "; ".join(string_items)
    if not isinstance(value, str):
        raise RoleCardValidationError(
            f"Contextual role card field '{field_name}' must be a string."
        )
    stripped = value.strip()
    if not stripped:
        raise RoleCardValidationError(
            f"Contextual role card field '{field_name}' must not be empty."
        )
    if len(stripped) > max_field_length:
        raise RoleCardValidationError(
            f"Contextual role card field '{field_name}' exceeds "
            f"{max_field_length} characters."
        )
    return stripped


def _validate_short_string_list(*,
                                value: Any,
                                field_name: str,
                                max_items: int,
                                max_field_length: int) -> list[str]:
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list):
        raise RoleCardValidationError(
            f"Contextual role card field '{field_name}' must be a list."
        )
    if not value:
        raise RoleCardValidationError(
            f"Contextual role card field '{field_name}' must not be empty."
        )
    if len(value) > max_items:
        raise RoleCardValidationError(
            f"Contextual role card field '{field_name}' must contain at most "
            f"{max_items} items."
        )
    return [
        _validate_short_string(
            value=item,
            field_name=f"{field_name}[]",
            max_field_length=max_field_length,
            max_items=max_items,
        )
        for item in value
    ]
