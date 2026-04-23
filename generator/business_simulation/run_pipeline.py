"""Unified business simulation generation pipeline.

Recommended CLI:
    python -m generator.business_simulation.run_pipeline \
    --business_idea "AI-powered website design platform for SMBs." \
    --num_consumers 20 \
    --consumer_seed 42 \
    --output business_simulation_pipeline.json \
    --pretty

With contextual identity enrichment:
    python -m generator.business_simulation.run_pipeline \
    --business_idea "AI-powered website design platform for SMBs." \
    --enable_contextual_identity \
    --llm_provider local \
    --llm_local_mode ollama \
    --llm_model llama3.1:8b \
    --output business_simulation_pipeline.json \
    --pretty
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .core.archetype_generation import (generate_agents_from_archetypes,
                                        load_archetype_config)
from .core.generation import load_schema_config
from .enrichment import (BaseLLMProvider, LLMProviderConfig, RoleCardConfig,
                         build_llm_provider,
                         enrich_agents_with_contextual_identity)
from .enrichment.schemas import SUPPORTED_CONTEXTUAL_IDENTITY_ROLES
from .roles.consumer.generate import generate_consumer_agents
from .roles.mentor.generate import generate_mentor_agents
from .roles.technical_expert.generate import generate_technical_expert_agents


ROLES_DIR = Path(__file__).with_name("roles")

OUTPUT_ROLES = (
    "consumer",
    "enterprise_buyer",
    "competitor",
    "investor",
    "supplier",
    "regulator",
    "technical_expert",
    "mentor",
)

BUSINESS_ARCHETYPE_ROLES = (
    "enterprise_buyer",
    "competitor",
    "investor",
    "supplier",
    "regulator",
)

PIPELINE_CONTEXTUAL_IDENTITY_ROLES = tuple(
    role for role in (
        "enterprise_buyer",
        "competitor",
        "supplier",
        "technical_expert",
    )
    if role in SUPPORTED_CONTEXTUAL_IDENTITY_ROLES
)

PIPELINE_STAGES = (
    "input_business_idea",
    "stochastic_consumer_generation",
    "deterministic_business_archetype_generation",
    "structured_technical_expert_generation",
    "structured_mentor_generation",
    "optional_contextual_identity_enrichment",
)


def run_business_simulation_pipeline(
    *,
    business_idea: str,
    num_consumers: int = 20,
    num_technical_experts: int = 1,
    num_mentors: int = 1,
    consumer_seed: int | None = None,
    expert_seed: int | None = None,
    mentor_seed: int | None = None,
    enable_contextual_identity: bool = False,
    llm_provider_config: LLMProviderConfig | None = None,
    role_card_config: RoleCardConfig | None = None,
    llm_provider: BaseLLMProvider | None = None,
) -> dict[str, Any]:
    """Run the full business simulation generation pipeline.

    The pipeline keeps three generation modes separate:
    stochastic consumers, deterministic business archetypes, and optional
    LLM-based contextual identities for currently supported roles.
    """
    _validate_pipeline_inputs(
        business_idea=business_idea,
        num_consumers=num_consumers,
        num_technical_experts=num_technical_experts,
        num_mentors=num_mentors,
        enable_contextual_identity=enable_contextual_identity,
        llm_provider_config=llm_provider_config,
        llm_provider=llm_provider,
    )

    agents_by_role: dict[str, list[dict[str, Any]]] = {
        role_name: [] for role_name in OUTPUT_ROLES
    }
    agents_by_role["consumer"] = _generate_consumers(
        num_consumers=num_consumers,
        seed=consumer_seed,
    )
    agents_by_role.update(_generate_business_archetypes())
    agents_by_role["technical_expert"] = _generate_technical_experts(
        num_technical_experts=num_technical_experts,
        seed=expert_seed,
    )
    agents_by_role["mentor"] = _generate_mentors(
        num_mentors=num_mentors,
        seed=mentor_seed,
    )

    if enable_contextual_identity:
        agents_by_role = _apply_contextual_identity_enrichment(
            agents_by_role=agents_by_role,
            business_idea=business_idea,
            llm_provider_config=llm_provider_config,
            role_card_config=role_card_config,
            llm_provider=llm_provider,
        )

    return {
        "metadata": {
            "generator": "business_simulation.run_pipeline",
            "mode": "unified_pipeline",
            "business_idea": business_idea,
            "pipeline_stages": list(PIPELINE_STAGES),
            "contextual_identity_enabled": enable_contextual_identity,
            "contextual_identity_roles": list(PIPELINE_CONTEXTUAL_IDENTITY_ROLES),
            "business_archetype_roles": list(BUSINESS_ARCHETYPE_ROLES),
            "stochastic_roles": ["consumer", "technical_expert", "mentor"],
            "generation_counts": {
                role_name: len(agents_by_role[role_name])
                for role_name in OUTPUT_ROLES
            },
            "seeds": {
                "consumer_seed": consumer_seed,
                "expert_seed": expert_seed,
                "mentor_seed": mentor_seed,
            },
            "llm_provider": (
                llm_provider_config.provider_type
                if enable_contextual_identity and llm_provider_config
                else None
            ),
            "llm_model": (
                llm_provider_config.model_name
                if enable_contextual_identity and llm_provider_config
                else None
            ),
        },
        "agents": {role_name: agents_by_role[role_name] for role_name in OUTPUT_ROLES},
    }


def build_argument_parser() -> argparse.ArgumentParser:
    """Create CLI parser for the unified business simulation pipeline."""
    parser = argparse.ArgumentParser(
        description="Run the unified business simulation generation pipeline."
    )
    parser.add_argument(
        "--business_idea",
        required=True,
        help="Natural-language business idea used as the simulation scenario.",
    )
    parser.add_argument(
        "--num_consumers",
        type=int,
        default=20,
        help="Number of stochastic consumer agents to generate.",
    )
    parser.add_argument(
        "--num_technical_experts",
        type=int,
        default=1,
        help="Number of structured technical expert agents to generate.",
    )
    parser.add_argument(
        "--num_mentors",
        type=int,
        default=1,
        help="Number of structured mentor agents to generate.",
    )
    parser.add_argument(
        "--consumer_seed",
        type=int,
        default=None,
        help="Random seed for consumer generation.",
    )
    parser.add_argument(
        "--expert_seed",
        type=int,
        default=None,
        help="Random seed for technical expert generation.",
    )
    parser.add_argument(
        "--mentor_seed",
        type=int,
        default=None,
        help="Random seed for mentor generation.",
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
    parser.add_argument(
        "--output",
        default=None,
        help="Optional path to save generated pipeline output as JSON.",
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

    llm_provider_config = None
    role_card_config = None
    if args.enable_contextual_identity:
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
        payload = run_business_simulation_pipeline(
            business_idea=args.business_idea,
            num_consumers=args.num_consumers,
            num_technical_experts=args.num_technical_experts,
            num_mentors=args.num_mentors,
            consumer_seed=args.consumer_seed,
            expert_seed=args.expert_seed,
            mentor_seed=args.mentor_seed,
            enable_contextual_identity=args.enable_contextual_identity,
            llm_provider_config=llm_provider_config,
            role_card_config=role_card_config,
        )
    except Exception as exc:
        parser.exit(status=1, message=f"error: pipeline generation failed: {exc}\n")

    _write_or_print_payload(payload, output=args.output, pretty=args.pretty)


def _generate_consumers(*, num_consumers: int, seed: int | None) -> list[dict[str, Any]]:
    config = load_schema_config(ROLES_DIR / "consumer" / "schema_config.json")
    return generate_consumer_agents(num_consumers, config, seed)


def _generate_business_archetypes() -> dict[str, list[dict[str, Any]]]:
    agents_by_role: dict[str, list[dict[str, Any]]] = {}
    for role_name in BUSINESS_ARCHETYPE_ROLES:
        schema_config = load_schema_config(ROLES_DIR / role_name / "schema_config.json")
        archetype_config = load_archetype_config(
            ROLES_DIR / role_name / "archetypes.json"
        )
        agents_by_role[role_name] = generate_agents_from_archetypes(
            schema_config=schema_config,
            archetype_config=archetype_config,
        )
    return agents_by_role


def _generate_technical_experts(
    *,
    num_technical_experts: int,
    seed: int | None,
) -> list[dict[str, Any]]:
    config = load_schema_config(ROLES_DIR / "technical_expert" / "schema_config.json")
    return generate_technical_expert_agents(num_technical_experts, config, seed)


def _generate_mentors(*, num_mentors: int, seed: int | None) -> list[dict[str, Any]]:
    config = load_schema_config(ROLES_DIR / "mentor" / "schema_config.json")
    return generate_mentor_agents(num_mentors, config, seed)


def _apply_contextual_identity_enrichment(
    *,
    agents_by_role: dict[str, list[dict[str, Any]]],
    business_idea: str,
    llm_provider_config: LLMProviderConfig | None,
    role_card_config: RoleCardConfig | None,
    llm_provider: BaseLLMProvider | None,
) -> dict[str, list[dict[str, Any]]]:
    provider = llm_provider
    if provider is None:
        if llm_provider_config is None:
            raise ValueError(
                "llm_provider_config is required when contextual identity is "
                "enabled and no llm_provider is supplied."
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

    enriched_by_role = {
        role_name: list(role_agents)
        for role_name, role_agents in agents_by_role.items()
    }
    for role_name in PIPELINE_CONTEXTUAL_IDENTITY_ROLES:
        enriched_by_role[role_name] = enrich_agents_with_contextual_identity(
            agents=agents_by_role[role_name],
            business_idea_description=business_idea,
            llm_provider=provider,
            role_card_config=effective_role_card_config,
        )

    return enriched_by_role


def _validate_pipeline_inputs(
    *,
    business_idea: str,
    num_consumers: int,
    num_technical_experts: int,
    num_mentors: int,
    enable_contextual_identity: bool,
    llm_provider_config: LLMProviderConfig | None,
    llm_provider: BaseLLMProvider | None,
) -> None:
    if not business_idea or not business_idea.strip():
        raise ValueError("business_idea must be a non-empty string.")
    if num_consumers < 0:
        raise ValueError("num_consumers must be non-negative.")
    if num_technical_experts < 0:
        raise ValueError("num_technical_experts must be non-negative.")
    if num_mentors < 0:
        raise ValueError("num_mentors must be non-negative.")
    if enable_contextual_identity and llm_provider is None:
        if llm_provider_config is None:
            raise ValueError(
                "llm_provider_config is required when contextual identity is "
                "enabled."
            )
        if not llm_provider_config.model_name:
            raise ValueError(
                "llm_provider_config.model_name is required when contextual "
                "identity is enabled."
            )


def _write_or_print_payload(
    payload: dict[str, Any],
    *,
    output: str | None,
    pretty: bool,
) -> None:
    if output:
        with Path(output).open("w", encoding="utf-8") as output_file:
            json.dump(
                payload,
                output_file,
                ensure_ascii=True,
                indent=2 if pretty else None,
            )
            if pretty:
                output_file.write("\n")
        return

    print(
        json.dumps(
            payload,
            ensure_ascii=True,
            indent=2 if pretty else None,
        )
    )


__all__ = [
    "BUSINESS_ARCHETYPE_ROLES",
    "OUTPUT_ROLES",
    "PIPELINE_CONTEXTUAL_IDENTITY_ROLES",
    "PIPELINE_STAGES",
    "build_argument_parser",
    "main",
    "run_business_simulation_pipeline",
]


if __name__ == "__main__":
    main()

