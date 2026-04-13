"""Generate all business-simulation roles into one JSON file.

Example:
    python -m generator.business_simulation.generate_all_roles \
      --num_agents_per_role 1 \
      --seed 42 \
      --business_idea "AI-powered website design platform for SMBs." \
      --enable_contextual_identity \
      --llm_provider local \
      --llm_local_mode ollama \
      --llm_model llama3.1:8b \
      --output business_simulation_agents.json \
      --pretty
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Callable, Optional

from .core import load_schema_config
from .enrichment import (LLMProviderConfig, RoleCardConfig, build_llm_provider,
                         enrich_agents_with_contextual_identity)
from .enrichment.schemas import SUPPORTED_CONTEXTUAL_IDENTITY_ROLES
from .roles.competitor.generate import generate_competitor_agents
from .roles.consumer.generate import generate_consumer_agents
from .roles.enterprise_buyer.generate import generate_enterprise_buyer_agents
from .roles.investor.generate import generate_investor_agents
from .roles.mentor.generate import generate_mentor_agents
from .roles.regulator.generate import generate_regulator_agents
from .roles.supplier.generate import generate_supplier_agents
from .roles.technical_expert.generate import generate_technical_expert_agents


GeneratorFn = Callable[[int, dict[str, Any], Optional[int]], list[dict[str, Any]]]

ROLE_GENERATORS: tuple[tuple[str, GeneratorFn], ...] = (
    ("consumer", generate_consumer_agents),
    ("enterprise_buyer", generate_enterprise_buyer_agents),
    ("competitor", generate_competitor_agents),
    ("investor", generate_investor_agents),
    ("supplier", generate_supplier_agents),
    ("regulator", generate_regulator_agents),
    ("technical_expert", generate_technical_expert_agents),
    ("mentor", generate_mentor_agents),
)


def generate_all_business_simulation_roles(
    *,
    num_agents_per_role: int,
    seed: int | None = None,
    business_idea: str | None = None,
    enable_contextual_identity: bool = False,
    llm_provider_config: LLMProviderConfig | None = None,
    role_card_config: RoleCardConfig | None = None,
) -> dict[str, Any]:
    """Generate all 8 roles, optionally enriching eligible role cards."""
    if num_agents_per_role < 0:
        raise ValueError("num_agents_per_role must be non-negative.")

    roles_dir = Path(__file__).with_name("roles")
    agents_by_role: dict[str, list[dict[str, Any]]] = {}
    flat_agents: list[dict[str, Any]] = []

    for role_name, generator in ROLE_GENERATORS:
        config = load_schema_config(roles_dir / role_name / "schema_config.json")
        role_agents = generator(num_agents_per_role, config, seed)
        agents_by_role[role_name] = role_agents
        flat_agents.extend(role_agents)

    if enable_contextual_identity:
        if not business_idea:
            raise ValueError(
                "business_idea is required when contextual identity is enabled."
            )
        if llm_provider_config is None:
            raise ValueError(
                "llm_provider_config is required when contextual identity is "
                "enabled."
            )
        provider = build_llm_provider(llm_provider_config)
        effective_role_card_config = role_card_config or RoleCardConfig(enabled=True)
        if not effective_role_card_config.enabled:
            effective_role_card_config = RoleCardConfig(
                enabled=True,
                strict_validation=effective_role_card_config.strict_validation,
                on_error=effective_role_card_config.on_error,
                max_list_items=effective_role_card_config.max_list_items,
                max_field_length=effective_role_card_config.max_field_length,
            )
        flat_agents = enrich_agents_with_contextual_identity(
            agents=flat_agents,
            business_idea_description=business_idea,
            llm_provider=provider,
            role_card_config=effective_role_card_config,
        )
        agents_by_role = _group_agents_by_role(flat_agents)

    return {
        "metadata": {
            "generator": "business_simulation.generate_all_roles",
            "roles": [role_name for role_name, _ in ROLE_GENERATORS],
            "num_agents_per_role": num_agents_per_role,
            "seed": seed,
            "contextual_identity_enabled": enable_contextual_identity,
            "contextual_identity_supported_roles": sorted(
                SUPPORTED_CONTEXTUAL_IDENTITY_ROLES
            ),
            "llm_provider": (
                llm_provider_config.provider_type if llm_provider_config else None
            ),
            "llm_model": (
                llm_provider_config.model_name if llm_provider_config else None
            ),
        },
        "agents": agents_by_role,
    }


def build_argument_parser() -> argparse.ArgumentParser:
    """Create CLI for all-role business simulation generation."""
    parser = argparse.ArgumentParser(
        description="Generate all 8 business-simulation roles into one JSON file."
    )
    parser.add_argument(
        "--num_agents_per_role",
        type=int,
        default=1,
        help="Number of agents to generate for each role.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Random seed used for each role generator.",
    )
    parser.add_argument(
        "--output",
        default="business_simulation_agents.json",
        help="Output JSON path.",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output with indentation.",
    )
    parser.add_argument(
        "--business_idea",
        default=None,
        help="Business idea used for optional contextual identity enrichment.",
    )
    parser.add_argument(
        "--enable_contextual_identity",
        action="store_true",
        help="Attach LLM-generated contextual_identity cards to supported roles.",
    )
    parser.add_argument(
        "--llm_provider",
        choices=("local", "api"),
        default="local",
        help="LLM provider type.",
    )
    parser.add_argument(
        "--llm_model",
        default=None,
        help="LLM model name.",
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
        help="How to handle contextual identity failures.",
    )
    parser.add_argument(
        "--no_contextual_strict_validation",
        action="store_true",
        help="Allow extra role-card fields in provider output.",
    )
    return parser


def main() -> None:
    """CLI entrypoint."""
    parser = build_argument_parser()
    args = parser.parse_args()

    llm_provider_config = None
    role_card_config = None
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
        llm_provider_config = LLMProviderConfig(
            provider_type=args.llm_provider,
            model_name=args.llm_model,
            base_url=args.llm_base_url or "",
            api_key_env=args.llm_api_key_env,
            timeout_seconds=args.llm_timeout_seconds,
            max_retries=args.llm_max_retries,
            local_mode=args.llm_local_mode,
        )
        role_card_config = RoleCardConfig(
            enabled=True,
            strict_validation=not args.no_contextual_strict_validation,
            on_error=args.contextual_on_error,
        )

    try:
        payload = generate_all_business_simulation_roles(
            num_agents_per_role=args.num_agents_per_role,
            seed=args.seed,
            business_idea=args.business_idea,
            enable_contextual_identity=args.enable_contextual_identity,
            llm_provider_config=llm_provider_config,
            role_card_config=role_card_config,
        )
    except Exception as exc:
        parser.exit(
            status=1,
            message=(
                f"error: all-role generation failed: {exc}\n"
                "hint: for LLM failures, ensure your provider is reachable or "
                "use --contextual_on_error skip to keep static agents.\n"
            ),
        )

    output_path = Path(args.output)
    with output_path.open("w", encoding="utf-8") as output_file:
        json.dump(
            payload,
            output_file,
            ensure_ascii=True,
            indent=2 if args.pretty else None,
        )
        if args.pretty:
            output_file.write("\n")
    print(f"Wrote {output_path}")


def _group_agents_by_role(agents: list[dict[str, Any]]
                          ) -> dict[str, list[dict[str, Any]]]:
    grouped = {role_name: [] for role_name, _ in ROLE_GENERATORS}
    for agent in agents:
        role = agent.get("role")
        if role in grouped:
            grouped[role].append(agent)
    return grouped


if __name__ == "__main__":
    main()
