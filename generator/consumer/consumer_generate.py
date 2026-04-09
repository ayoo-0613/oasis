"""Config-driven generator for general consumer agents."""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Any

try:
    from .validator import validate_generated_agent, validate_schema_config
except ImportError:  # pragma: no cover - supports direct script execution
    from validator import validate_generated_agent, validate_schema_config


GROUP_OUTPUT_KEYS = (
    "demographic",
    "behavioral_traits",
    "consumption_preferences",
)


def load_schema_config(config_path: str | Path) -> dict[str, Any]:
    """Load and validate a schema config from disk."""
    with Path(config_path).open("r", encoding="utf-8") as config_file:
        config = json.load(config_file)

    validate_schema_config(config)
    return config


def sample_from_distribution(distribution_dict: dict[str, float],
                             rng: random.Random) -> str:
    """Sample a categorical value from a validated probability distribution."""
    threshold = rng.random()
    cumulative = 0.0
    last_key = ""
    for key, weight in distribution_dict.items():
        cumulative += weight
        last_key = key
        if threshold <= cumulative:
            return key

    return last_key


def generate_consumer_agents(num_agents: int,
                             config: dict[str, Any],
                             seed: int | None = None) -> list[dict[str, Any]]:
    """Generate a batch of structured consumer agents."""
    if num_agents < 0:
        raise ValueError("num_agents must be non-negative.")

    validate_schema_config(config)
    rng = random.Random(seed)
    return [
        _generate_single_agent(index=index, config=config, rng=rng)
        for index in range(1, num_agents + 1)
    ]


def save_agents(agents: list[dict[str, Any]],
                output_path: str | Path,
                pretty: bool = False) -> None:
    """Persist generated agents to JSON."""
    with Path(output_path).open("w", encoding="utf-8") as output_file:
        json.dump(
            agents,
            output_file,
            ensure_ascii=True,
            indent=2 if pretty else None,
        )
        if pretty:
            output_file.write("\n")


def build_argument_parser() -> argparse.ArgumentParser:
    """Create the command-line interface for consumer generation."""
    parser = argparse.ArgumentParser(
        description="Generate structured general consumer agents."
    )
    parser.add_argument(
        "--config",
        default=str(Path(__file__).with_name("schema_config.json")),
        help="Path to the consumer schema configuration JSON file.",
    )
    parser.add_argument(
        "--num_agents",
        type=int,
        required=True,
        help="Number of consumer agents to generate.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Random seed for deterministic generation.",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Optional path to save generated agents as JSON.",
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

    config = load_schema_config(args.config)
    agents = generate_consumer_agents(
        num_agents=args.num_agents,
        config=config,
        seed=args.seed,
    )

    if args.output:
        save_agents(agents, args.output, pretty=args.pretty)
    else:
        print(
            json.dumps(
                agents,
                ensure_ascii=True,
                indent=2 if args.pretty else None,
            )
        )


def _generate_single_agent(index: int,
                           config: dict[str, Any],
                           rng: random.Random) -> dict[str, Any]:
    sampled_fields: dict[str, str] = {}

    for field in config["sampling_order"]:
        sampled_fields[field] = _sample_field_value(
            field=field,
            sampled_fields=sampled_fields,
            config=config,
            rng=rng,
        )

    agent = {
        "agent_id": f"consumer_{index:06d}",
        "role": "consumer",
    }
    for group_name in GROUP_OUTPUT_KEYS:
        agent[group_name] = {}

    for field, value in sampled_fields.items():
        group_name = config["field_groups"][field]
        agent[group_name][field] = value

    validate_generated_agent(agent, config)
    return agent


def _sample_field_value(field: str,
                        sampled_fields: dict[str, str],
                        config: dict[str, Any],
                        rng: random.Random) -> str:
    conditional_config = config["conditional_ratios"].get(field)
    if conditional_config:
        parent_field = conditional_config["parent_field"]
        parent_value = sampled_fields[parent_field]
        distribution = conditional_config["distributions"][parent_value]
        return sample_from_distribution(distribution, rng)

    # Category labels are fully config-driven, so schema v2 renames such as
    # low/medium/high -> shallow/moderate/deep require no generator changes.
    distribution = config["marginal_ratios"][field]
    return sample_from_distribution(distribution, rng)


if __name__ == "__main__":
    main()
