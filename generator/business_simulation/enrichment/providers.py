"""LLM provider adapters and JSON extraction utilities."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from typing import Any

from .base import (BaseLLMProvider, JSONExtractionError, LLMProviderConfig,
                   LLMProviderError)


def extract_json_object(raw_output: str) -> dict[str, Any]:
    """Extract and parse the first JSON object from provider text."""
    candidate = raw_output.strip()
    if candidate.startswith("```"):
        candidate = _strip_markdown_fence(candidate)

    start_index = candidate.find("{")
    if start_index == -1:
        raise JSONExtractionError("Provider output does not contain a JSON object.")

    end_index = _find_matching_object_end(candidate, start_index)
    if end_index == -1:
        raise JSONExtractionError("Provider output contains an unterminated JSON object.")

    json_payload = candidate[start_index:end_index + 1]
    try:
        parsed = json.loads(json_payload)
    except json.JSONDecodeError as exc:
        raise JSONExtractionError(
            f"Provider output is not valid JSON: {exc}."
        ) from exc
    if not isinstance(parsed, dict):
        raise JSONExtractionError("Provider output JSON must be an object.")
    return parsed


class LocalLLMProvider(BaseLLMProvider):
    """Local HTTP LLM provider with Ollama and OpenAI-compatible modes."""

    def __init__(self, config: LLMProviderConfig):
        self.config = config
        if not self.config.model_name:
            raise LLMProviderError("Local LLM provider requires model_name.")

    def generate_json(self,
                      prompt: str,
                      system_prompt: str | None = None) -> dict[str, Any]:
        """Generate JSON using a local HTTP endpoint."""
        if self.config.local_mode == "ollama":
            return self._generate_ollama_json(prompt, system_prompt)
        if self.config.local_mode == "openai_compatible":
            if not self.config.base_url:
                raise LLMProviderError(
                    "OpenAI-compatible local provider requires base_url."
                )
            return _generate_openai_compatible_json(
                config=self.config,
                prompt=prompt,
                system_prompt=system_prompt,
                api_key=None,
            )
        return self._generate_generic_json(prompt, system_prompt)

    def _generate_ollama_json(self,
                              prompt: str,
                              system_prompt: str | None) -> dict[str, Any]:
        base_url = self.config.base_url or "http://localhost:11434"
        url = f"{base_url.rstrip('/')}/api/generate"
        payload = {
            "model": self.config.model_name,
            "prompt": prompt,
            "stream": False,
            "format": "json",
        }
        if system_prompt:
            payload["system"] = system_prompt

        response = _post_json_with_retries(url=url, payload=payload, config=self.config)
        if isinstance(response, dict):
            response_text = response.get("response")
            if isinstance(response_text, str):
                return extract_json_object(response_text)
            # Some local adapters return the JSON object directly.
            if all(isinstance(key, str) for key in response):
                return response
        raise LLMProviderError("Ollama response did not contain JSON text.")

    def _generate_generic_json(self,
                               prompt: str,
                               system_prompt: str | None) -> dict[str, Any]:
        if not self.config.base_url:
            raise LLMProviderError("Generic local provider requires base_url.")
        payload = {
            "model": self.config.model_name,
            "prompt": prompt,
            "system_prompt": system_prompt,
            "response_format": "json_object",
        }
        response = _post_json_with_retries(
            url=self.config.base_url,
            payload=payload,
            config=self.config,
        )
        return _parse_text_or_object_response(response)


class APILLMProvider(BaseLLMProvider):
    """Vendor-neutral OpenAI-compatible chat completions provider."""

    def __init__(self, config: LLMProviderConfig):
        self.config = config
        if not self.config.model_name:
            raise LLMProviderError("API LLM provider requires model_name.")
        if not self.config.base_url:
            raise LLMProviderError("API LLM provider requires base_url.")

    def generate_json(self,
                      prompt: str,
                      system_prompt: str | None = None) -> dict[str, Any]:
        """Generate JSON using an OpenAI-compatible chat completions API."""
        api_key = os.getenv(self.config.api_key_env) if self.config.api_key_env else None
        return _generate_openai_compatible_json(
            config=self.config,
            prompt=prompt,
            system_prompt=system_prompt,
            api_key=api_key,
        )


def build_llm_provider(config: LLMProviderConfig | dict[str, Any]) -> BaseLLMProvider:
    """Build an LLM provider from a config object or dict."""
    provider_config = (
        config if isinstance(config, LLMProviderConfig)
        else LLMProviderConfig(**config)
    )
    if provider_config.provider_type == "local":
        return LocalLLMProvider(provider_config)
    if provider_config.provider_type == "api":
        return APILLMProvider(provider_config)
    raise LLMProviderError(
        f"Unsupported LLM provider type '{provider_config.provider_type}'."
    )


def build_llm_provider_config_from_env(prefix: str = "BUSINESS_SIM_LLM_"
                                       ) -> LLMProviderConfig:
    """Build provider config from environment variables."""
    return LLMProviderConfig(
        provider_type=os.getenv(f"{prefix}PROVIDER_TYPE", "local"),  # type: ignore[arg-type]
        model_name=os.getenv(f"{prefix}MODEL_NAME", ""),
        base_url=os.getenv(f"{prefix}BASE_URL", ""),
        api_key_env=os.getenv(f"{prefix}API_KEY_ENV"),
        timeout_seconds=float(os.getenv(f"{prefix}TIMEOUT_SECONDS", "60")),
        max_retries=int(os.getenv(f"{prefix}MAX_RETRIES", "1")),
        local_mode=os.getenv(f"{prefix}LOCAL_MODE", "ollama"),  # type: ignore[arg-type]
    )


def _generate_openai_compatible_json(*,
                                     config: LLMProviderConfig,
                                     prompt: str,
                                     system_prompt: str | None,
                                     api_key: str | None) -> dict[str, Any]:
    url = f"{config.base_url.rstrip('/')}/chat/completions"
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    payload = {
        "model": config.model_name,
        "messages": messages,
        "response_format": {"type": "json_object"},
    }
    headers = dict(config.extra_headers)
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    response = _post_json_with_retries(
        url=url,
        payload=payload,
        config=config,
        headers=headers,
    )
    return _parse_openai_compatible_response(response)


def _post_json_with_retries(*,
                            url: str,
                            payload: dict[str, Any],
                            config: LLMProviderConfig,
                            headers: dict[str, str] | None = None) -> Any:
    attempts = max(1, config.max_retries + 1)
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            return _post_json(
                url=url,
                payload=payload,
                timeout_seconds=config.timeout_seconds,
                headers=headers,
            )
        except (urllib.error.URLError, TimeoutError, LLMProviderError) as exc:
            last_error = exc
            if attempt + 1 < attempts:
                time.sleep(min(0.5 * (attempt + 1), 2.0))
    raise LLMProviderError(f"LLM provider request failed: {last_error}") from last_error


def _post_json(*,
               url: str,
               payload: dict[str, Any],
               timeout_seconds: float,
               headers: dict[str, str] | None = None) -> Any:
    request_headers = {"Content-Type": "application/json"}
    if headers:
        request_headers.update(headers)
    request = urllib.request.Request(
        url=url,
        data=json.dumps(payload).encode("utf-8"),
        headers=request_headers,
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        body = response.read().decode("utf-8")
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return {"text": body}


def _parse_openai_compatible_response(response: Any) -> dict[str, Any]:
    if not isinstance(response, dict):
        raise LLMProviderError("OpenAI-compatible response must be an object.")
    try:
        content = response["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise LLMProviderError(
            "OpenAI-compatible response missing choices[0].message.content."
        ) from exc
    if not isinstance(content, str):
        raise LLMProviderError("OpenAI-compatible response content must be text.")
    return extract_json_object(content)


def _parse_text_or_object_response(response: Any) -> dict[str, Any]:
    if isinstance(response, dict):
        for key in ("json", "response", "text", "content"):
            value = response.get(key)
            if isinstance(value, dict):
                return value
            if isinstance(value, str):
                return extract_json_object(value)
        return response
    if isinstance(response, str):
        return extract_json_object(response)
    raise LLMProviderError("Provider response must be a JSON object or text.")


def _strip_markdown_fence(text: str) -> str:
    lines = text.splitlines()
    if lines and lines[0].strip().startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()


def _find_matching_object_end(text: str, start_index: int) -> int:
    depth = 0
    in_string = False
    escaped = False
    for index in range(start_index, len(text)):
        char = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return index
    return -1
