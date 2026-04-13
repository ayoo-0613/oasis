"""Regulator role generator."""

__all__ = [
    "DEFAULT_CONFIG_PATH",
    "generate_regulator_agents",
    "load_schema_config",
    "main",
]


def __getattr__(name: str):
    if name in __all__:
        from . import generate
        return getattr(generate, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
