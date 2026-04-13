"""Shared config-driven generation core for discrete structured agents.

Example CLI usage:
    python -m generator.business_simulation.roles.consumer.generate --num_agents 5 --seed 42
    python -m generator.business_simulation.roles.enterprise_buyer.generate --num_agents 5 --seed 42
    python -m generator.business_simulation.roles.competitor.generate --num_agents 5 --seed 42
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Any, Callable

from .validator import (resolve_role_definition, validate_generated_agent,
                        validate_schema_config)


AgentEnricher = Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]]


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


def generate_agents(num_agents: int,
                    config: dict[str, Any],
                    seed: int | None = None,
                    enricher: AgentEnricher | None = None) -> list[dict[str, Any]]:
    """Generate a batch of structured agents for the provided schema config."""
    if num_agents < 0:
        raise ValueError("num_agents must be non-negative.")

    validate_schema_config(config)
    rng = random.Random(seed)
    return [
        _generate_single_agent(
            index=index,
            config=config,
            rng=rng,
            enricher=enricher,
        )
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


def build_generator_argument_parser(*,
                                    description: str,
                                    default_config_path: str | Path
                                    ) -> argparse.ArgumentParser:
    """Create a standard CLI for schema-driven agent generation."""
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        "--config",
        default=str(default_config_path),
        help="Path to the schema configuration JSON file.",
    )
    parser.add_argument(
        "--num_agents",
        type=int,
        required=True,
        help="Number of agents to generate.",
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
    parser.add_argument(
        "--business_idea",
        default=None,
        help=(
            "Business idea description used for optional contextual identity "
            "generation."
        ),
    )
    parser.add_argument(
        "--enable_contextual_identity",
        action="store_true",
        help="Attach LLM-generated contextual_identity role cards when enabled.",
    )
    parser.add_argument(
        "--llm_provider",
        choices=("local", "api"),
        default="local",
        help="LLM provider type for contextual identity generation.",
    )
    parser.add_argument(
        "--llm_model",
        default=None,
        help="LLM model name for contextual identity generation.",
    )
    parser.add_argument(
        "--llm_base_url",
        default=None,
        help="Base URL for the local or API LLM provider.",
    )
    parser.add_argument(
        "--llm_api_key_env",
        default=None,
        help="Environment variable containing the API key, if needed.",
    )
    parser.add_argument(
        "--llm_local_mode",
        choices=("ollama", "openai_compatible", "generic"),
        default="ollama",
        help="Local provider protocol adapter.",
    )
    parser.add_argument(
        "--llm_timeout_seconds",
        type=float,
        default=60.0,
        help="LLM HTTP timeout in seconds.",
    )
    parser.add_argument(
        "--llm_max_retries",
        type=int,
        default=1,
        help="Maximum LLM retry count after the first attempt.",
    )
    parser.add_argument(
        "--contextual_on_error",
        choices=("raise", "skip"),
        default="raise",
        help="How to handle contextual identity provider or validation errors.",
    )
    parser.add_argument(
        "--no_contextual_strict_validation",
        action="store_true",
        help="Allow extra role-card fields in provider output.",
    )
    parser.add_argument(
        "--contextual_max_list_items",
        type=int,
        default=5,
        help="Maximum list items allowed in contextual role-card list fields.",
    )
    parser.add_argument(
        "--contextual_max_field_length",
        type=int,
        default=180,
        help="Maximum character length for contextual role-card string fields.",
    )
    return parser


def run_generator_cli(*,
                      description: str,
                      default_config_path: str | Path,
                      generator: Callable[[int, dict[str, Any], int | None],
                                          list[dict[str, Any]]]) -> None:
    """Run a role-specific generator via the standard CLI surface."""
    parser = build_generator_argument_parser(
        description=description,
        default_config_path=default_config_path,
    )
    args = parser.parse_args()

    config = load_schema_config(args.config)
    agents = generator(args.num_agents, config, args.seed)
    if args.enable_contextual_identity:
        if not args.business_idea:
            parser.error(
                "--business_idea is required when "
                "--enable_contextual_identity is set."
            )
        if not args.llm_model:
            parser.error(
                "--llm_model is required when --enable_contextual_identity "
                "is set."
            )
        agents = _enrich_agents_from_cli_args(agents, args)

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


def _enrich_agents_from_cli_args(agents: list[dict[str, Any]],
                                 args: argparse.Namespace
                                 ) -> list[dict[str, Any]]:
    from ..enrichment import (LLMProviderConfig, RoleCardConfig,
                              build_llm_provider,
                              enrich_agents_with_contextual_identity)

    provider = build_llm_provider(
        LLMProviderConfig(
            provider_type=args.llm_provider,
            model_name=args.llm_model,
            base_url=args.llm_base_url or "",
            api_key_env=args.llm_api_key_env,
            timeout_seconds=args.llm_timeout_seconds,
            max_retries=args.llm_max_retries,
            local_mode=args.llm_local_mode,
        )
    )
    role_card_config = RoleCardConfig(
        enabled=True,
        strict_validation=not args.no_contextual_strict_validation,
        on_error=args.contextual_on_error,
        max_list_items=args.contextual_max_list_items,
        max_field_length=args.contextual_max_field_length,
    )
    return enrich_agents_with_contextual_identity(
        agents=agents,
        business_idea_description=args.business_idea,
        llm_provider=provider,
        role_card_config=role_card_config,
    )


def enrich_agent_profile(agent: dict[str, Any],
                         config: dict[str, Any],
                         enricher: AgentEnricher | None = None) -> dict[str, Any]:
    """Optional post-processing hook for future LLM-based enrichment.

    This hook is intentionally inert unless an explicit enricher callback is
    provided by a future caller. The current generators only emit structured
    discrete attributes.
    """
    if enricher is None:
        return agent

    enriched_agent = enricher(agent, config)
    validate_generated_agent(enriched_agent, config)
    return enriched_agent


def _generate_single_agent(index: int,
                           config: dict[str, Any],
                           rng: random.Random,
                           enricher: AgentEnricher | None) -> dict[str, Any]:
    role_definition = resolve_role_definition(config)
    sampled_fields: dict[str, str] = {}

    for field in config["sampling_order"]:
        sampled_fields[field] = _sample_field_value(
            field=field,
            sampled_fields=sampled_fields,
            config=config,
            rng=rng,
        )

    agent = {
        "agent_id": f"{role_definition.agent_id_prefix}_{index:06d}",
        "role": role_definition.role,
    }
    for group_name in role_definition.output_groups:
        agent[group_name] = {}

    for field, value in sampled_fields.items():
        group_name = config["field_groups"][field]
        agent[group_name][field] = value

    validate_generated_agent(agent, config)
    return enrich_agent_profile(agent, config, enricher=enricher)


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

    distribution = config["marginal_ratios"][field]
    return sample_from_distribution(distribution, rng)
