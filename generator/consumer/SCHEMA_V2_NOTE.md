# Consumer Schema V2 Note

This schema upgrade keeps the existing generator architecture unchanged while improving interpretability under classical consumer behavior theory.

What changed:
- Added `perceived_behavioral_control` as a `behavioral_traits` field and sampled it conditionally on `education_group`.
- Upgraded `novelty_adoption` from 3 categories to the standard 5 diffusion-of-innovations categories.
- Replaced `purchase_planning_style` values with a more theory-aligned decision-process taxonomy:
  `impulsive`, `habitual`, `limited_problem_solving`, `extended_problem_solving`.
- Renamed `information_search_depth` values from `low/medium/high` to `shallow/moderate/deep`.
- Kept `decision_speed` for compatibility and annotated it in metadata as a downstream process indicator.

Why it changed:
- The new structure is more interpretable in terms of involvement, perceived risk, Theory of Planned Behavior, and diffusion of innovations.
- The schema remains discrete, ratio-based, single-parent conditional, and easy to validate in the current codebase.

Theory-driven changes:
- `involvement_level -> information_search_depth`
- `involvement_level -> purchase_planning_style`
- `risk_sensitivity -> decision_speed`
- `risk_sensitivity -> brand_loyalty`
- `education_group -> perceived_behavioral_control`
- `age_group -> novelty_adoption`
- `age_group -> social_influence_susceptibility`

Future v3 candidates:
- Add multi-parent conditionals for `perceived_behavioral_control` using income and region.
- Consider downstream uses of `perceived_behavioral_control` for channel behavior or innovation adoption once multi-parent support exists.
- Separate stable traits from process outcomes more explicitly if downstream consumers need stronger ontology distinctions.
