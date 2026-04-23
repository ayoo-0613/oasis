# Business Simulation Pipeline

`generator.business_simulation.run_pipeline` is the preferred high-level
entrypoint for generating one complete simulation population.

## Pipeline Stages

1. **Input**: accept a natural-language `business_idea` as the scenario.
2. **Demand-side population**: generate `consumer` agents with the existing
   probabilistic schema-driven generator.
3. **Business-side canonical roles**: generate deterministic archetypes for
   `enterprise_buyer`, `competitor`, `investor`, `supplier`, and `regulator`.
4. **Expert/advisory roles**: generate structured `technical_expert` and
   `mentor` agents with the existing probabilistic schema-driven generator.
5. **Optional contextual identity**: when enabled, attach LLM-generated
   `contextual_identity` cards only to supported roles.

## Role Strategy

`consumer` remains probabilistic because demand-side simulation needs population
variation across many individual-like agents.

The five business-side roles use deterministic archetypes because they represent
canonical market institutions and strategic postures. Archetypes make these
participants stable, theory-grounded, and easier to compare across runs.

`technical_expert` is generated as a structured schema-based agent first. If
contextual identity is enabled, the LLM only instantiates the expert identity for
the current business scenario; it does not replace the structured attributes.

`mentor` remains schema-based for now. The current enrichment layer does not
support mentor contextual identity, so the unified pipeline does not attempt it.

## Contextual Identity Support

Current supported enrichment roles are:

- `enterprise_buyer`
- `competitor`
- `supplier`
- `technical_expert`

The pipeline intentionally does not enrich `consumer`, `investor`, `regulator`,
or `mentor`.

## Example

```bash
python -m generator.business_simulation.run_pipeline \
  --business_idea "AI-powered website design platform for SMBs." \
  --num_consumers 20 \
  --consumer_seed 42 \
  --output business_simulation_pipeline.json \
  --pretty
```

With local LLM enrichment:

```bash
python -m generator.business_simulation.run_pipeline \
  --business_idea "AI-powered website design platform for SMBs." \
  --enable_contextual_identity \
  --llm_provider local \
  --llm_local_mode ollama \
  --llm_model llama3.1:8b \
  --output business_simulation_pipeline.json \
  --pretty
```

