# All Roles Generation Test

Use this command to generate all 8 business-simulation roles into one JSON file.
The four contextual-identity roles (`enterprise_buyer`, `competitor`,
`supplier`, and `technical_expert`) will be enriched through the configured LLM.

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

If Ollama is not running, start it first:

```bash
ollama serve
ollama pull llama3.1:8b
```

If the LLM fails but you still want a JSON with all static agents, add:

```bash
--contextual_on_error skip
```

The output JSON shape is:

```json
{
  "metadata": {
    "generator": "business_simulation.generate_all_roles",
    "roles": ["consumer", "..."],
    "contextual_identity_enabled": true
  },
  "agents": {
    "consumer": [],
    "enterprise_buyer": [],
    "competitor": [],
    "investor": [],
    "supplier": [],
    "regulator": [],
    "technical_expert": [],
    "mentor": []
  }
}
```
