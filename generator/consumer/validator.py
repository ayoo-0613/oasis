"""Validation helpers for consumer agent generation."""

from __future__ import annotations

from typing import Any


ALLOWED_FIELD_GROUPS = {
    "demographic",
    "behavioral_traits",
    "consumption_preferences",
}


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


def validate_schema_config(config: dict[str, Any]) -> None:
    """Validate the consumer generator config."""
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

    if set(schema) != set(field_groups):
        missing_group_mappings = set(schema).difference(field_groups)
        extra_group_mappings = set(field_groups).difference(schema)
        raise ValueError(
            "Config 'field_groups' must map exactly the schema fields. "
            f"Missing mappings: {sorted(missing_group_mappings)}. "
            f"Unexpected mappings: {sorted(extra_group_mappings)}."
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
        if group not in ALLOWED_FIELD_GROUPS:
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
    if agent.get("role") != "consumer":
        raise ValueError(
            f"Generated agent role must be 'consumer', got '{agent.get('role')}'."
        )

    agent_id = agent.get("agent_id")
    if not isinstance(agent_id, str) or not agent_id.startswith("consumer_"):
        raise ValueError(
            "Generated agent must include an 'agent_id' starting with "
            "'consumer_'."
        )

    schema = config["schema"]
    field_groups = config["field_groups"]

    for group_name in ALLOWED_FIELD_GROUPS:
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
        for group_name in ALLOWED_FIELD_GROUPS
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
