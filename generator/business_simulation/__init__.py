"""Business simulation agent generation package.

This package keeps role-specific generators lazily imported so
`python -m generator.business_simulation.roles.<role>.generate` does not load
the target module during parent-package initialization.
"""

from .core import (RoleDefinition, enrich_agent_profile, generate_agents,
                   generate_agents_from_archetypes, load_archetype_config,
                   load_schema_config, resolve_role_definition, save_agents,
                   validate_archetype_config, validate_distribution,
                   validate_generated_agent, validate_schema_config)
from .enrichment import (BaseLLMProvider, ContextualIdentityError,
                         LLMProviderConfig, RoleCardConfig,
                         enrich_agents_with_contextual_identity)

__all__ = [
    "BaseLLMProvider",
    "ContextualIdentityError",
    "LLMProviderConfig",
    "RoleDefinition",
    "RoleCardConfig",
    "enrich_agent_profile",
    "enrich_agents_with_contextual_identity",
    "generate_agents",
    "generate_agents_from_archetypes",
    "generate_competitor_agents",
    "generate_consumer_agents",
    "generate_enterprise_buyer_agents",
    "generate_investor_agents",
    "generate_supplier_agents",
    "generate_regulator_agents",
    "generate_technical_expert_agents",
    "generate_mentor_agents",
    "load_archetype_config",
    "load_schema_config",
    "resolve_role_definition",
    "save_agents",
    "validate_archetype_config",
    "validate_distribution",
    "validate_generated_agent",
    "validate_schema_config",
]


def __getattr__(name: str):
    if name == "generate_consumer_agents":
        from .roles.consumer.generate import generate_consumer_agents
        return generate_consumer_agents
    if name == "generate_enterprise_buyer_agents":
        from .roles.enterprise_buyer.generate import (
            generate_enterprise_buyer_agents,
        )
        return generate_enterprise_buyer_agents
    if name == "generate_competitor_agents":
        from .roles.competitor.generate import generate_competitor_agents
        return generate_competitor_agents
    if name == "generate_investor_agents":
        from .roles.investor.generate import generate_investor_agents
        return generate_investor_agents
    if name == "generate_supplier_agents":
        from .roles.supplier.generate import generate_supplier_agents
        return generate_supplier_agents
    if name == "generate_regulator_agents":
        from .roles.regulator.generate import generate_regulator_agents
        return generate_regulator_agents
    if name == "generate_technical_expert_agents":
        from .roles.technical_expert.generate import (
            generate_technical_expert_agents,
        )
        return generate_technical_expert_agents
    if name == "generate_mentor_agents":
        from .roles.mentor.generate import generate_mentor_agents
        return generate_mentor_agents
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
