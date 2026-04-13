"""Shared types and exceptions for contextual identity enrichment."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Literal


ProviderType = Literal["local", "api"]
LocalMode = Literal["ollama", "openai_compatible", "generic"]
OnErrorMode = Literal["raise", "skip"]


class ContextualIdentityError(RuntimeError):
    """Base error for contextual identity enrichment failures."""


class LLMProviderError(ContextualIdentityError):
    """Raised when an LLM provider cannot produce usable output."""


class JSONExtractionError(ContextualIdentityError):
    """Raised when provider text cannot be parsed as a JSON object."""


class RoleCardValidationError(ContextualIdentityError):
    """Raised when a contextual role card violates its role schema."""


@dataclass(frozen=True)
class LLMProviderConfig:
    """Configuration for local or API-based JSON-generating LLM providers."""

    provider_type: ProviderType = "local"
    model_name: str = ""
    base_url: str = ""
    api_key_env: str | None = None
    timeout_seconds: float = 60.0
    max_retries: int = 1
    local_mode: LocalMode = "ollama"
    extra_headers: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class RoleCardConfig:
    """Configuration for contextual role-card validation and error handling."""

    enabled: bool = False
    strict_validation: bool = True
    on_error: OnErrorMode = "raise"
    max_list_items: int = 5
    max_field_length: int = 180


class BaseLLMProvider(ABC):
    """Provider interface for prompt-in, JSON-object-out LLM adapters."""

    @abstractmethod
    def generate_json(self,
                      prompt: str,
                      system_prompt: str | None = None) -> dict[str, Any]:
        """Generate and parse a JSON object from a provider response."""
