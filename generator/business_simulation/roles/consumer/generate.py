"""CLI and wrapper for structured consumer generation.

Example:
    python -m generator.business_simulation.roles.consumer.generate --num_agents 10 --seed 7 --pretty
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from generator.business_simulation.core.generation import (generate_agents,
                                                           load_schema_config,
                                                           run_generator_cli)


def generate_consumer_agents(num_agents: int,
                             config: dict[str, Any],
                             seed: int | None = None) -> list[dict[str, Any]]:
    """Generate a batch of structured consumer agents."""
    return generate_agents(num_agents=num_agents, config=config, seed=seed)


DEFAULT_CONFIG_PATH = Path(__file__).with_name("schema_config.json")


def main() -> None:
    """CLI entrypoint."""
    run_generator_cli(
        description="Generate structured general consumer agents.",
        default_config_path=DEFAULT_CONFIG_PATH,
        generator=generate_consumer_agents,
    )


if __name__ == "__main__":
    main()
