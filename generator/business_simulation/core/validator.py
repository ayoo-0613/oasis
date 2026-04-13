"""Validation helpers for config-driven structured agent generation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


DEFAULT_OPTIONAL_ENRICHMENT_FIELDS = (
    "behavioral_summary",
    "persona_description",
    "narrative_profile",
    "contextual_identity",
)


@dataclass(frozen=True)
class RoleDefinition:
    """Resolved role metadata required by the generic generator pipeline."""

    role: str
    agent_id_prefix: str
    output_groups: tuple[str, ...]
    optional_enrichment_fields: tuple[str, ...]


def validate_distribution(dist: dict[str, float],
                          tolerance: float = 1e-6) -> None:
    """Validate a categorical probability distribution."""
    if not dist:
        raise ValueError("Distribution must not be empty.")

    total = 0.0
    for key, value in dist.items():
        if not isinstance(value, (int, float)):
            raise TypeError(
                f"Distribution value for '{key}' must be numeric, got "
                f"{type(value).__name__}."
            )
        if value < 0:
            raise ValueError(
                f"Distribution value for '{key}' must be non-negative, got "
                f"{value}."
            )
        total += float(value)

    if abs(total - 1.0) > tolerance:
        raise ValueError(
            f"Distribution must sum to 1.0 within tolerance {tolerance}, "
            f"got {total:.12f}."
        )


def resolve_role_definition(config: dict[str, Any]) -> RoleDefinition:
    """Resolve role metadata from config with compatibility fallbacks."""
    metadata = config.get("metadata", {})
    if not isinstance(metadata, dict):
        raise ValueError("Config 'metadata' must be an object.")

    field_groups = config.get("field_groups", {})
    if not isinstance(field_groups, dict):
        field_groups = {}

    role = metadata.get("role")
    if not role:
        generator_name = metadata.get("generator_name", "")
        if generator_name.endswith("_generate"):
            role = generator_name.removesuffix("_generate")
        elif generator_name:
            role = generator_name
        else:
            role = "agent"

    agent_id_prefix = metadata.get("agent_id_prefix", role)

    output_groups = metadata.get("output_groups")
    if output_groups is None:
        output_groups = tuple(_ordered_unique(field_groups.values()))
    else:
        output_groups = tuple(output_groups)

    enrichment_config = metadata.get("enrichment", {})
    if not isinstance(enrichment_config, dict):
        raise ValueError("Config 'metadata.enrichment' must be an object.")
    optional_enrichment_fields = enrichment_config.get(
        "optional_output_fields",
        DEFAULT_OPTIONAL_ENRICHMENT_FIELDS,
    )
    if "contextual_identity" not in optional_enrichment_fields:
        optional_enrichment_fields = (
            *tuple(optional_enrichment_fields),
            "contextual_identity",
        )

    return RoleDefinition(
        role=role,
        agent_id_prefix=agent_id_prefix,
        output_groups=tuple(output_groups),
        optional_enrichment_fields=tuple(optional_enrichment_fields),
    )


def validate_schema_config(config: dict[str, Any]) -> None:
    """Validate a role-specific generator config."""
    required_top_level_keys = {
        "metadata",
        "schema",
        "marginal_ratios",
        "conditional_ratios",
        "sampling_order",
        "field_groups",
    }
    missing_keys = required_top_level_keys.difference(config)
    if missing_keys:
        raise KeyError(
            f"Schema config missing required top-level keys: "
            f"{sorted(missing_keys)}."
        )

    schema = config["schema"]
    marginal_ratios = config["marginal_ratios"]
    conditional_ratios = config["conditional_ratios"]
    sampling_order = config["sampling_order"]
    field_groups = config["field_groups"]
    if not isinstance(schema, dict) or not schema:
        raise ValueError("Config 'schema' must be a non-empty object.")
    if not isinstance(marginal_ratios, dict):
        raise ValueError("Config 'marginal_ratios' must be an object.")
    if not isinstance(conditional_ratios, dict):
        raise ValueError("Config 'conditional_ratios' must be an object.")
    if not isinstance(sampling_order, list) or not sampling_order:
        raise ValueError("Config 'sampling_order' must be a non-empty array.")
    if not isinstance(field_groups, dict) or not field_groups:
        raise ValueError("Config 'field_groups' must be a non-empty object.")

    role_definition = resolve_role_definition(config)
    _validate_role_metadata(role_definition)

    if set(schema) != set(field_groups):
        missing_group_mappings = set(schema).difference(field_groups)
        extra_group_mappings = set(field_groups).difference(schema)
        raise ValueError(
            "Config 'field_groups' must map exactly the schema fields. "
            f"Missing mappings: {sorted(missing_group_mappings)}. "
            f"Unexpected mappings: {sorted(extra_group_mappings)}."
        )

    configured_groups = set(field_groups.values())
    expected_groups = set(role_definition.output_groups)
    if configured_groups != expected_groups:
        missing_groups = sorted(expected_groups.difference(configured_groups))
        extra_groups = sorted(configured_groups.difference(expected_groups))
        raise ValueError(
            "Config metadata output groups must match field_groups exactly. "
            f"Missing: {missing_groups}. Extra: {extra_groups}."
        )

    if set(sampling_order) != set(schema):
        missing_sampled_fields = set(schema).difference(sampling_order)
        extra_sampled_fields = set(sampling_order).difference(schema)
        raise ValueError(
            "Config 'sampling_order' must contain every schema field exactly "
            f"once. Missing: {sorted(missing_sampled_fields)}. Extra: "
            f"{sorted(extra_sampled_fields)}."
        )

    if len(sampling_order) != len(set(sampling_order)):
        raise ValueError("Config 'sampling_order' must not contain duplicates.")

    for field, legal_values in schema.items():
        if not isinstance(legal_values, list) or not legal_values:
            raise ValueError(
                f"Schema field '{field}' must define a non-empty list of "
                "legal values."
            )
        if len(legal_values) != len(set(legal_values)):
            raise ValueError(
                f"Schema field '{field}' contains duplicate legal values."
            )

        group = field_groups[field]
        if group not in role_definition.output_groups:
            raise ValueError(
                f"Field '{field}' is mapped to unsupported group '{group}'."
            )

        has_marginal = field in marginal_ratios
        has_conditional = field in conditional_ratios
        if not has_marginal and not has_conditional:
            raise ValueError(
                f"Field '{field}' must define either marginal_ratios or "
                "conditional_ratios."
            )

    for field, dist in marginal_ratios.items():
        if field not in schema:
            raise ValueError(
                f"Marginal ratios define unknown field '{field}'."
            )
        _validate_distribution_keys(
            dist=dist,
            legal_values=schema[field],
            context=f"marginal_ratios.{field}",
        )
        validate_distribution(dist)

    sampling_positions = {
        field: index for index, field in enumerate(sampling_order)
    }
    for target_field, conditional_config in conditional_ratios.items():
        if target_field not in schema:
            raise ValueError(
                f"Conditional ratios define unknown target field "
                f"'{target_field}'."
            )
        if not isinstance(conditional_config, dict):
            raise ValueError(
                f"Conditional ratios for '{target_field}' must be an object."
            )
        parent_field = conditional_config.get("parent_field")
        distributions = conditional_config.get("distributions")
        if parent_field not in schema:
            raise ValueError(
                f"Conditional ratios for '{target_field}' reference unknown "
                f"parent field '{parent_field}'."
            )
        if sampling_positions[parent_field] >= sampling_positions[target_field]:
            raise ValueError(
                f"Parent field '{parent_field}' must appear before target "
                f"field '{target_field}' in sampling_order."
            )
        if not isinstance(distributions, dict) or not distributions:
            raise ValueError(
                f"Conditional ratios for '{target_field}' must define a "
                "non-empty 'distributions' object."
            )

        parent_legal_values = set(schema[parent_field])
        target_legal_values = schema[target_field]
        provided_parent_values = set(distributions)
        if provided_parent_values != parent_legal_values:
            missing_parent_values = sorted(
                parent_legal_values.difference(provided_parent_values)
            )
            extra_parent_values = sorted(
                provided_parent_values.difference(parent_legal_values)
            )
            raise ValueError(
                f"Conditional ratios for '{target_field}' must provide "
                f"distributions for every '{parent_field}' value. Missing: "
                f"{missing_parent_values}. Extra: {extra_parent_values}."
            )

        for parent_value, dist in distributions.items():
            _validate_distribution_keys(
                dist=dist,
                legal_values=target_legal_values,
                context=(
                    f"conditional_ratios.{target_field}.distributions."
                    f"{parent_value}"
                ),
            )
            validate_distribution(dist)


def validate_generated_agent(agent: dict[str, Any], config: dict[str, Any]) -> None:
    """Validate a generated agent against the configured schema."""
    role_definition = resolve_role_definition(config)
    if agent.get("role") != role_definition.role:
        raise ValueError(
            f"Generated agent role must be '{role_definition.role}', got "
            f"'{agent.get('role')}'."
        )

    agent_id = agent.get("agent_id")
    expected_prefix = f"{role_definition.agent_id_prefix}_"
    if not isinstance(agent_id, str) or not agent_id.startswith(expected_prefix):
        raise ValueError(
            "Generated agent must include an 'agent_id' starting with "
            f"'{expected_prefix}'."
        )

    schema = config["schema"]
    field_groups = config["field_groups"]
    allowed_top_level_keys = {
        "agent_id",
        "role",
        *role_definition.output_groups,
        *role_definition.optional_enrichment_fields,
    }
    actual_top_level_keys = set(agent)
    unexpected_top_level_keys = sorted(
        actual_top_level_keys.difference(allowed_top_level_keys)
    )
    if unexpected_top_level_keys:
        raise ValueError(
            "Generated agent contains unsupported top-level keys: "
            f"{unexpected_top_level_keys}."
        )

    for group_name in role_definition.output_groups:
        group_payload = agent.get(group_name)
        if not isinstance(group_payload, dict):
            raise ValueError(
                f"Generated agent group '{group_name}' must be an object."
            )

    for field, legal_values in schema.items():
        group_name = field_groups[field]
        group_payload = agent[group_name]
        if field not in group_payload:
            raise ValueError(
                f"Generated agent missing field '{field}' in group "
                f"'{group_name}'."
            )
        field_value = group_payload[field]
        if field_value not in legal_values:
            raise ValueError(
                f"Generated agent field '{field}' has illegal value "
                f"'{field_value}'. Expected one of {legal_values}."
            )

    expected_fields_by_group: dict[str, set[str]] = {
        group_name: {
            field for field, mapped_group in field_groups.items()
            if mapped_group == group_name
        }
        for group_name in role_definition.output_groups
    }

    for group_name, expected_fields in expected_fields_by_group.items():
        actual_fields = set(agent[group_name])
        if actual_fields != expected_fields:
            missing_fields = sorted(expected_fields.difference(actual_fields))
            extra_fields = sorted(actual_fields.difference(expected_fields))
            raise ValueError(
                f"Generated agent group '{group_name}' fields do not match "
                f"schema. Missing: {missing_fields}. Extra: {extra_fields}."
            )


def _validate_distribution_keys(*, dist: dict[str, float],
                                legal_values: list[str],
                                context: str) -> None:
    if not isinstance(dist, dict) or not dist:
        raise ValueError(f"{context} must be a non-empty object.")

    legal_value_set = set(legal_values)
    dist_key_set = set(dist)
    if dist_key_set != legal_value_set:
        missing_values = sorted(legal_value_set.difference(dist_key_set))
        extra_values = sorted(dist_key_set.difference(legal_value_set))
        raise ValueError(
            f"{context} must define exactly the legal schema values. Missing: "
            f"{missing_values}. Extra: {extra_values}."
        )


def _ordered_unique(values: Any) -> list[str]:
    seen: set[str] = set()
    ordered_values: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            ordered_values.append(value)
    return ordered_values


def _validate_role_metadata(role_definition: RoleDefinition) -> None:
    if not isinstance(role_definition.role, str) or not role_definition.role:
        raise ValueError("Resolved role must be a non-empty string.")
    if (not isinstance(role_definition.agent_id_prefix, str)
            or not role_definition.agent_id_prefix):
        raise ValueError("Resolved agent_id_prefix must be a non-empty string.")
    if not role_definition.output_groups:
        raise ValueError("Resolved output_groups must be non-empty.")
    if len(role_definition.output_groups) != len(set(role_definition.output_groups)):
        raise ValueError("Resolved output_groups must not contain duplicates.")
    for group_name in role_definition.output_groups:
        if not isinstance(group_name, str) or not group_name:
            raise ValueError(
                "Every resolved output group must be a non-empty string."
            )
    if len(role_definition.optional_enrichment_fields) != len(
            set(role_definition.optional_enrichment_fields)):
        raise ValueError(
            "Optional enrichment output fields must not contain duplicates."
        )
    for field_name in role_definition.optional_enrichment_fields:
        if not isinstance(field_name, str) or not field_name:
            raise ValueError(
                "Optional enrichment output fields must be non-empty strings."
            )
