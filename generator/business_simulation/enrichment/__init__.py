"""Optional scenario-conditioned contextual identity enrichment."""

from .base import (BaseLLMProvider, ContextualIdentityError,
                   JSONExtractionError, LLMProviderConfig, LLMProviderError,
                   RoleCardConfig, RoleCardValidationError)
from .config import (ContextualIdentityEnrichmentConfig,
                     load_contextual_identity_enrichment_config)
from .pipeline import enrich_agents_with_contextual_identity
from .prompts import (CONTEXTUAL_ROLE_CARD_SYSTEM_PROMPT,
                      build_competitor_role_card_prompt,
                      build_contextual_role_card_prompt,
                      build_enterprise_buyer_role_card_prompt,
                      build_supplier_role_card_prompt,
                      build_technical_expert_role_card_prompt)
from .providers import (APILLMProvider, LocalLLMProvider, build_llm_provider,
                        build_llm_provider_config_from_env,
                        extract_json_object)
from .schemas import (ROLE_CARD_SCHEMAS, SUPPORTED_CONTEXTUAL_IDENTITY_ROLES,
                      get_role_card_schema)
from .validator import validate_contextual_role_card

__all__ = [
    "APILLMProvider",
    "BaseLLMProvider",
    "CONTEXTUAL_ROLE_CARD_SYSTEM_PROMPT",
    "ContextualIdentityEnrichmentConfig",
    "ContextualIdentityError",
    "JSONExtractionError",
    "LLMProviderConfig",
    "LLMProviderError",
    "LocalLLMProvider",
    "ROLE_CARD_SCHEMAS",
    "RoleCardConfig",
    "RoleCardValidationError",
    "SUPPORTED_CONTEXTUAL_IDENTITY_ROLES",
    "build_competitor_role_card_prompt",
    "build_contextual_role_card_prompt",
    "build_enterprise_buyer_role_card_prompt",
    "build_llm_provider",
    "build_llm_provider_config_from_env",
    "build_supplier_role_card_prompt",
    "build_technical_expert_role_card_prompt",
    "enrich_agents_with_contextual_identity",
    "extract_json_object",
    "get_role_card_schema",
    "load_contextual_identity_enrichment_config",
    "validate_contextual_role_card",
]
