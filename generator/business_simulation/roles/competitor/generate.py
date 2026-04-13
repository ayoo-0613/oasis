"""CLI and wrapper for structured competitor generation.

Example:
    python -m generator.business_simulation.roles.competitor.generate --num_agents 10 --seed 7 --pretty
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from generator.business_simulation.core.generation import (generate_agents,
                                                           load_schema_config,
                                                           run_generator_cli)


DEFAULT_CONFIG_PATH = Path(__file__).with_name("schema_config.json")


def generate_competitor_agents(num_agents: int,
                               config: dict[str, Any],
                               seed: int | None = None
                               ) -> list[dict[str, Any]]:
    """Generate a batch of structured competitor agents."""
    return generate_agents(num_agents=num_agents, config=config, seed=seed)


def main() -> None:
    """CLI entrypoint."""
    run_generator_cli(
        description="Generate structured competitor agents.",
        default_config_path=DEFAULT_CONFIG_PATH,
        generator=generate_competitor_agents,
    )


__all__ = [
    "DEFAULT_CONFIG_PATH",
    "generate_competitor_agents",
    "load_schema_config",
    "main",
]


if __name__ == "__main__":
    main()
