"""Regulator role generator."""

__all__ = [
    "DEFAULT_ARCHETYPES_CONFIG_PATH",
    "DEFAULT_CONFIG_PATH",
    "DEFAULT_SCHEMA_CONFIG_PATH",
    "generate_regulator_archetypes",
    "generate_regulator_agents",
    "load_archetype_config",
    "load_schema_config",
    "main",
]


def __getattr__(name: str):
    archetype_names = {
        "DEFAULT_ARCHETYPES_CONFIG_PATH",
        "DEFAULT_SCHEMA_CONFIG_PATH",
        "generate_regulator_archetypes",
        "load_archetype_config",
    }
    if name in archetype_names:
        from . import generate_archetypes
        return getattr(generate_archetypes, name)
    if name in __all__:
        from . import generate
        return getattr(generate, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
