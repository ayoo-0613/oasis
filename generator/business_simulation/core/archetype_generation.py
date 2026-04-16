"""Deterministic archetype-based generation for business simulation roles.

This module intentionally runs beside the stochastic generator in
``generation.py``. It uses the same role schemas and final agent validator, but
field assignments come from curated archetype libraries instead of probability
distributions.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .archetype_validator import validate_archetype_config
from .generation import load_schema_config, save_agents
from .validator import resolve_role_definition, validate_generated_agent


def load_archetype_config(path: str | Path) -> dict[str, Any]:
    """Load an archetype config JSON file from disk."""
    with Path(path).open("r", encoding="utf-8") as config_file:
        return json.load(config_file)


def generate_agents_from_archetypes(
    schema_config: dict[str, Any],
    archetype_config: dict[str, Any],
) -> list[dict[str, Any]]:
    """Generate one deterministic agent for each configured archetype."""
    validate_archetype_config(archetype_config, schema_config)
    role_definition = resolve_role_definition(schema_config)

    agents: list[dict[str, Any]] = []
    for index, archetype in enumerate(archetype_config["archetypes"], start=1):
        agent = {
            "agent_id": f"{role_definition.agent_id_prefix}_{index:06d}",
            "role": role_definition.role,
            "archetype_id": archetype["archetype_id"],
            "archetype_name": archetype["display_name"],
        }
        for group_name in role_definition.output_groups:
            agent[group_name] = {}

        for field, value in archetype["fields"].items():
            group_name = schema_config["field_groups"][field]
            agent[group_name][field] = value

        validate_generated_agent(agent, schema_config)
        agents.append(agent)

    return agents


def build_archetype_argument_parser(
    *,
    description: str,
    default_schema_config_path: str | Path,
    default_archetypes_config_path: str | Path,
) -> argparse.ArgumentParser:
    """Create a standard CLI for deterministic archetype generation."""
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        "--schema_config",
        default=str(default_schema_config_path),
        help="Path to the role schema_config.json file.",
    )
    parser.add_argument(
        "--archetypes_config",
        default=str(default_archetypes_config_path),
        help="Path to the role archetypes.json file.",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Optional path to save generated archetype agents as JSON.",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output with indentation.",
    )
    return parser


def run_archetype_generator_cli(
    *,
    description: str,
    default_schema_config_path: str | Path,
    default_archetypes_config_path: str | Path,
) -> None:
    """Run a role-specific deterministic archetype generator CLI."""
    parser = build_archetype_argument_parser(
        description=description,
        default_schema_config_path=default_schema_config_path,
        default_archetypes_config_path=default_archetypes_config_path,
    )
    args = parser.parse_args()

    try:
        schema_config = load_schema_config(args.schema_config)
        archetype_config = load_archetype_config(args.archetypes_config)
        agents = generate_agents_from_archetypes(schema_config, archetype_config)
    except Exception as exc:
        parser.exit(status=1, message=f"error: archetype generation failed: {exc}\n")

    if args.output:
        save_agents(agents, args.output, pretty=args.pretty)
        return

    print(
        json.dumps(
            agents,
            ensure_ascii=True,
            indent=2 if args.pretty else None,
        )
    )

