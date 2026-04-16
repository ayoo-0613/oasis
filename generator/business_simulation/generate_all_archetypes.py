"""Generate deterministic archetypes for selected business-simulation roles.

Example:
    python -m generator.business_simulation.generate_all_archetypes \
    --output business_simulation_archetypes.json \
    --pretty
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Callable

from .core.archetype_generation import (generate_agents_from_archetypes,
                                        load_archetype_config)
from .core.generation import load_schema_config


ArchetypeGeneratorFn = Callable[[dict[str, Any], dict[str, Any]],
                                list[dict[str, Any]]]

ARCHETYPE_ROLES = (
    "enterprise_buyer",
    "competitor",
    "investor",
    "supplier",
    "regulator",
)


def generate_all_business_simulation_archetypes() -> dict[str, Any]:
    """Generate deterministic archetype agents for the five supported roles."""
    roles_dir = Path(__file__).with_name("roles")
    agents_by_role: dict[str, list[dict[str, Any]]] = {}

    for role_name in ARCHETYPE_ROLES:
        schema_config = load_schema_config(roles_dir / role_name / "schema_config.json")
        archetype_config = load_archetype_config(roles_dir / role_name / "archetypes.json")
        agents_by_role[role_name] = generate_agents_from_archetypes(
            schema_config=schema_config,
            archetype_config=archetype_config,
        )

    return {
        "metadata": {
            "generator": "business_simulation.generate_all_archetypes",
            "mode": "archetype",
            "roles": list(ARCHETYPE_ROLES),
        },
        "agents": agents_by_role,
    }


def build_argument_parser() -> argparse.ArgumentParser:
    """Create CLI for all-role deterministic archetype generation."""
    parser = argparse.ArgumentParser(
        description=(
            "Generate deterministic archetype agents for enterprise_buyer, "
            "competitor, investor, supplier, and regulator."
        )
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


def main() -> None:
    """CLI entrypoint."""
    parser = build_argument_parser()
    args = parser.parse_args()

    try:
        payload = generate_all_business_simulation_archetypes()
    except Exception as exc:
        parser.exit(status=1, message=f"error: all-archetype generation failed: {exc}\n")

    if args.output:
        with Path(args.output).open("w", encoding="utf-8") as output_file:
            json.dump(
                payload,
                output_file,
                ensure_ascii=True,
                indent=2 if args.pretty else None,
            )
            if args.pretty:
                output_file.write("\n")
        return

    print(
        json.dumps(
            payload,
            ensure_ascii=True,
            indent=2 if args.pretty else None,
        )
    )


__all__ = [
    "ARCHETYPE_ROLES",
    "build_argument_parser",
    "generate_all_business_simulation_archetypes",
    "main",
]


if __name__ == "__main__":
    main()
