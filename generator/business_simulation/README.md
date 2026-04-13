# Business Simulation Generators

This package generates static structured agents for business simulation roles.
Static generation remains config-driven and deterministic when a seed is
provided.

## Contextual Role Cards

Contextual role cards are an optional enrichment layer. They run after static
agent generation and attach a `contextual_identity` object to supported roles.
They do not overwrite static attributes and they do not evaluate whether a
business idea is good or bad.

Supported contextual identity roles:

- `enterprise_buyer`
- `competitor`
- `supplier`
- `technical_expert`

The role card is a compact JSON object that grounds the static profile in the
current business scenario. For example, an abstract `enterprise_buyer` becomes a
plausible type of organization and use case for the supplied market scenario.

## Python Usage

```python
from generator.business_simulation.enrichment import (
    LLMProviderConfig,
    RoleCardConfig,
    build_llm_provider,
    enrich_agents_with_contextual_identity,
)
from generator.business_simulation.roles.enterprise_buyer import (
    generate_enterprise_buyer_agents,
    load_schema_config,
)

config = load_schema_config("generator/business_simulation/roles/enterprise_buyer/schema_config.json")
agents = generate_enterprise_buyer_agents(5, config, seed=42)

provider = build_llm_provider(LLMProviderConfig(
    provider_type="local",
    local_mode="ollama",
    model_name="llama3",
    base_url="http://localhost:11434",
))

agents = enrich_agents_with_contextual_identity(
    agents=agents,
    business_idea_description="AI-powered website design platform for SMBs.",
    llm_provider=provider,
    role_card_config=RoleCardConfig(enabled=True, on_error="skip"),
)
```

## CLI Usage

Static generation remains unchanged:

```bash
python -m generator.business_simulation.roles.enterprise_buyer.generate \
  --num_agents 20 \
  --seed 42 \
  --pretty
```

Contextual identity generation is opt-in:

```bash
python -m generator.business_simulation.roles.enterprise_buyer.generate \
  --num_agents 20 \
  --seed 42 \
  --business_idea "AI-powered website design platform for SMBs." \
  --enable_contextual_identity \
  --llm_provider local \
  --llm_local_mode ollama \
  --llm_model llama3 \
  --output enterprise_buyers.json \
  --pretty
```

For OpenAI-compatible API providers, configure a base URL and optional API key
environment variable:

```bash
export BUSINESS_SIM_API_KEY="..."

python -m generator.business_simulation.roles.competitor.generate \
  --num_agents 10 \
  --seed 42 \
  --business_idea "AI-powered website design platform for SMBs." \
  --enable_contextual_identity \
  --llm_provider api \
  --llm_model your-model-name \
  --llm_base_url "https://your-provider.example/v1" \
  --llm_api_key_env BUSINESS_SIM_API_KEY \
  --pretty
```

## Provider Notes

The provider layer is vendor-neutral. `LocalLLMProvider` supports Ollama-style,
OpenAI-compatible local serving, and a generic HTTP JSON adapter. `APILLMProvider`
uses an OpenAI-compatible chat completions request shape with configurable
`base_url`, `model_name`, and `api_key_env`.

If the provider is unavailable, set `--contextual_on_error skip` or use
`RoleCardConfig(on_error="skip")` to keep static agents and omit failed role
cards with a warning.

An example JSON config is available at
`generator/business_simulation/enrichment/contextual_identity_config.example.json`.
YAML is not supported because this package currently avoids adding dependencies.

## Generate All Roles

To generate all 8 roles into one JSON file, use the all-role test runner:

```bash
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
```

This generates all static roles and enriches only the supported contextual
identity roles: `enterprise_buyer`, `competitor`, `supplier`, and
`technical_expert`. See `generator/business_simulation/ALL_ROLES_TEST.md` for a
short runnable test document.
