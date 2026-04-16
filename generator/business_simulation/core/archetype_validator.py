"""Validation for deterministic role archetype libraries.

Archetype configs are a parallel input format to the stochastic
``schema_config.json`` files. They must assign every schema field exactly once
using legal discrete values from the role schema.
"""

from __future__ import annotations

from typing import Any


ALLOWED_ARCHETYPE_METADATA_KEYS = {
    "role",
    "_comment",
    "description",
    "reference_notes",
}

ALLOWED_ARCHETYPE_ITEM_KEYS = {
    "archetype_id",
    "display_name",
    "fields",
    "_comment",
    "summary",
    "theory_tags",
    "reference_notes",
}


def validate_archetype_config(
    archetype_config: dict[str, Any],
    schema_config: dict[str, Any],
) -> None:
    """Validate a deterministic archetype config against a role schema."""
    if not isinstance(archetype_config, dict):
        raise TypeError("Archetype config must be an object.")
    if not isinstance(schema_config, dict):
        raise TypeError("Schema config must be an object.")

    required_top_level_keys = {"metadata", "archetypes"}
    missing_keys = required_top_level_keys.difference(archetype_config)
    if missing_keys:
        raise KeyError(
            "Archetype config missing required top-level keys: "
            f"{sorted(missing_keys)}."
        )

    metadata = archetype_config["metadata"]
    archetypes = archetype_config["archetypes"]
    if not isinstance(metadata, dict):
        raise ValueError("Archetype config 'metadata' must be an object.")
    if not isinstance(archetypes, list) or not archetypes:
        raise ValueError("Archetype config 'archetypes' must be a non-empty array.")

    unexpected_metadata_keys = sorted(
        set(metadata).difference(ALLOWED_ARCHETYPE_METADATA_KEYS)
    )
    if unexpected_metadata_keys:
        raise ValueError(
            "Archetype metadata contains unsupported keys: "
            f"{unexpected_metadata_keys}."
        )

    schema_metadata = schema_config.get("metadata", {})
    schema_role = schema_metadata.get("role")
    archetype_role = metadata.get("role")
    if archetype_role != schema_role:
        raise ValueError(
            "Archetype metadata role must match schema metadata role. "
            f"Expected '{schema_role}', got '{archetype_role}'."
        )

    schema = schema_config.get("schema", {})
    if not isinstance(schema, dict) or not schema:
        raise ValueError("Schema config 'schema' must be a non-empty object.")

    schema_fields = set(schema)
    seen_archetype_ids: set[str] = set()
    for index, archetype in enumerate(archetypes, start=1):
        _validate_archetype_item(
            archetype=archetype,
            index=index,
            schema=schema,
            schema_fields=schema_fields,
            seen_archetype_ids=seen_archetype_ids,
        )


def _validate_archetype_item(
    *,
    archetype: Any,
    index: int,
    schema: dict[str, list[str]],
    schema_fields: set[str],
    seen_archetype_ids: set[str],
) -> None:
    if not isinstance(archetype, dict):
        raise ValueError(f"Archetype item #{index} must be an object.")

    required_keys = {"archetype_id", "display_name", "fields"}
    missing_keys = required_keys.difference(archetype)
    if missing_keys:
        raise KeyError(
            f"Archetype item #{index} missing required keys: "
            f"{sorted(missing_keys)}."
        )

    unexpected_keys = sorted(set(archetype).difference(ALLOWED_ARCHETYPE_ITEM_KEYS))
    if unexpected_keys:
        raise ValueError(
            f"Archetype item #{index} contains unsupported keys: "
            f"{unexpected_keys}."
        )

    archetype_id = archetype["archetype_id"]
    if not isinstance(archetype_id, str) or not archetype_id:
        raise ValueError(f"Archetype item #{index} archetype_id must be a string.")
    if archetype_id in seen_archetype_ids:
        raise ValueError(f"Duplicate archetype_id '{archetype_id}'.")
    seen_archetype_ids.add(archetype_id)

    display_name = archetype["display_name"]
    if not isinstance(display_name, str) or not display_name:
        raise ValueError(f"Archetype '{archetype_id}' display_name must be a string.")

    fields = archetype["fields"]
    if not isinstance(fields, dict):
        raise ValueError(f"Archetype '{archetype_id}' fields must be an object.")

    actual_fields = set(fields)
    if actual_fields != schema_fields:
        missing_fields = sorted(schema_fields.difference(actual_fields))
        extra_fields = sorted(actual_fields.difference(schema_fields))
        raise ValueError(
            f"Archetype '{archetype_id}' fields must define every schema field "
            f"exactly once. Missing: {missing_fields}. Extra: {extra_fields}."
        )

    for field, value in fields.items():
        if field.startswith("_") or field in {
            "summary",
            "theory_tags",
            "reference_notes",
        }:
            raise ValueError(
                f"Archetype '{archetype_id}' descriptive key '{field}' must not "
                "appear inside fields."
            )
        legal_values = schema[field]
        if value not in legal_values:
            raise ValueError(
                f"Archetype '{archetype_id}' field '{field}' has illegal value "
                f"'{value}'. Expected one of {legal_values}."
            )

