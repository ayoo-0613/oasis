"""CLI and wrapper for deterministic investor archetypes.

Example:
    python -m generator.business_simulation.roles.investor.generate_archetypes --pretty
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from generator.business_simulation.core.archetype_generation import (
    generate_agents_from_archetypes,
    load_archetype_config,
    run_archetype_generator_cli,
)
from generator.business_simulation.core.generation import load_schema_config


DEFAULT_SCHEMA_CONFIG_PATH = Path(__file__).with_name("schema_config.json")
DEFAULT_ARCHETYPES_CONFIG_PATH = Path(__file__).with_name("archetypes.json")


def generate_investor_archetypes(
    schema_config: dict[str, Any],
    archetype_config: dict[str, Any],
) -> list[dict[str, Any]]:
    """Generate deterministic investor archetype agents."""
    return generate_agents_from_archetypes(schema_config, archetype_config)


def main() -> None:
    """CLI entrypoint."""
    run_archetype_generator_cli(
        description="Generate deterministic investor archetype agents.",
        default_schema_config_path=DEFAULT_SCHEMA_CONFIG_PATH,
        default_archetypes_config_path=DEFAULT_ARCHETYPES_CONFIG_PATH,
    )


__all__ = [
    "DEFAULT_ARCHETYPES_CONFIG_PATH",
    "DEFAULT_SCHEMA_CONFIG_PATH",
    "generate_investor_archetypes",
    "load_archetype_config",
    "load_schema_config",
    "main",
]


if __name__ == "__main__":
    main()
