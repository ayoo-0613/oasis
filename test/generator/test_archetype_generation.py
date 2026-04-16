from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from generator.business_simulation.core import (load_schema_config,
                                                validate_generated_agent)
from generator.business_simulation.core.archetype_generation import (
    generate_agents_from_archetypes,
    load_archetype_config,
)
from generator.business_simulation.core.archetype_validator import (
    validate_archetype_config,
)
from generator.business_simulation.generate_all_archetypes import (
    ARCHETYPE_ROLES,
    generate_all_business_simulation_archetypes,
)


ROOT_DIR = Path(__file__).resolve().parents[2]
ROLES_DIR = ROOT_DIR / "generator" / "business_simulation" / "roles"


def test_archetype_config_validation_success_for_all_supported_roles():
    for role_name in ARCHETYPE_ROLES:
        schema_config, archetype_config = _load_role_configs(role_name)

        validate_archetype_config(archetype_config, schema_config)


def test_archetype_config_rejects_unknown_field():
    schema_config, archetype_config = _load_role_configs("enterprise_buyer")
    invalid_config = deepcopy(archetype_config)
    invalid_config["archetypes"][0]["fields"]["unknown_field"] = "medium"

    with pytest.raises(ValueError, match="Extra"):
        validate_archetype_config(invalid_config, schema_config)


def test_archetype_config_rejects_missing_field():
    schema_config, archetype_config = _load_role_configs("enterprise_buyer")
    invalid_config = deepcopy(archetype_config)
    del invalid_config["archetypes"][0]["fields"]["company_size"]

    with pytest.raises(ValueError, match="Missing"):
        validate_archetype_config(invalid_config, schema_config)


def test_archetype_config_rejects_illegal_field_value():
    schema_config, archetype_config = _load_role_configs("enterprise_buyer")
    invalid_config = deepcopy(archetype_config)
    invalid_config["archetypes"][0]["fields"]["company_size"] = "not_legal"

    with pytest.raises(ValueError, match="illegal value"):
        validate_archetype_config(invalid_config, schema_config)


def test_archetype_config_rejects_duplicate_archetype_id():
    schema_config, archetype_config = _load_role_configs("enterprise_buyer")
    invalid_config = deepcopy(archetype_config)
    invalid_config["archetypes"][1]["archetype_id"] = (
        invalid_config["archetypes"][0]["archetype_id"]
    )

    with pytest.raises(ValueError, match="Duplicate archetype_id"):
        validate_archetype_config(invalid_config, schema_config)


def test_archetype_config_rejects_role_mismatch():
    schema_config, archetype_config = _load_role_configs("enterprise_buyer")
    invalid_config = deepcopy(archetype_config)
    invalid_config["metadata"]["role"] = "competitor"

    with pytest.raises(ValueError, match="role must match"):
        validate_archetype_config(invalid_config, schema_config)


def test_archetype_generation_succeeds_and_validates_for_each_role():
    for role_name in ARCHETYPE_ROLES:
        schema_config, archetype_config = _load_role_configs(role_name)

        agents = generate_agents_from_archetypes(schema_config, archetype_config)

        assert len(agents) == len(archetype_config["archetypes"])
        for index, agent in enumerate(agents, start=1):
            assert agent["role"] == role_name
            assert agent["agent_id"].endswith(f"{index:06d}")
            assert "archetype_id" in agent
            assert "archetype_name" in agent
            validate_generated_agent(agent, schema_config)


def test_generate_all_archetypes_output_shape():
    payload = generate_all_business_simulation_archetypes()

    assert payload["metadata"]["generator"] == (
        "business_simulation.generate_all_archetypes"
    )
    assert payload["metadata"]["mode"] == "archetype"
    assert payload["metadata"]["roles"] == list(ARCHETYPE_ROLES)
    assert set(payload["agents"]) == set(ARCHETYPE_ROLES)
    for role_name in ARCHETYPE_ROLES:
        assert len(payload["agents"][role_name]) == 3


def _load_role_configs(role_name: str) -> tuple[dict[str, Any], dict[str, Any]]:
    role_dir = ROLES_DIR / role_name
    return (
        load_schema_config(role_dir / "schema_config.json"),
        load_archetype_config(role_dir / "archetypes.json"),
    )

