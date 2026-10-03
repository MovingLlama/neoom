"""Tests für die Zuordnung von Gateway-Einstellungen zu Entitäten."""

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.neoom.const import DOMAIN
from custom_components.neoom.helpers import classify_setting

from .conftest import ENTRY_DATA, INVERTER_ID, SITE_ID, make_beaam_config, mock_apis


@pytest.mark.parametrize(
    ("key", "value", "platform", "known"),
    [
        ("OPERATING_MODE_EMS", "griid_controlled", "select", True),
        ("BATTERY_CHARGE_FROM_GRID_ALLOWED", "false", "switch", True),
        ("GRIID_EV_DEPARTURE_TIME", "11:30", "time", True),
        ("GRIID_CHARGING_ENERGY", "17000", "number", True),
        ("LOCK_TIME", "1800", "number", True),
        # Heuristik für unbekannte Einstellungen
        ("SOME_START_TIME", "06:00", "time", False),
        ("SOME_FEATURE", "TRUE", "switch", False),
        ("SOME_LIMIT", "5", "number", False),
        ("SOME_FACTOR", "0.5", "number", False),
        ("SOME_POWER", "abc", "number", False),
        ("SOME_LABEL", "abc", None, False),
        # Ein Wert true/false wird nur noch ein Schalter, nicht zusätzlich eine Zahl
        ("SOME_POWER_ENABLED", "true", "switch", False),
    ],
)
def test_classify_setting(key: str, value: str, platform: str | None, known: bool) -> None:
    """Jede Einstellung landet auf genau einer Plattform; bekannte kommen aus der Tabelle."""
    spec, is_known = classify_setting(key, value)
    assert (spec.platform if spec else None) == platform
    assert is_known is known


SETTINGS = [
    {"key": "LOCK_TIME", "value": "1800"},
    {"key": "POWER_THRESHOLD_NORMAL_OP", "value": "2000"},
    {"key": "GRIID_CHARGING_ENERGY", "value": "17000"},
    {"key": "BATTERY_CHARGE_FROM_GRID_ALLOWED", "value": "false"},
    {"key": "UNKNOWN_LIMIT", "value": "5"},
    {"key": "UNKNOWN_FEATURE", "value": "true"},
]


async def test_setting_entities(hass: HomeAssistant, aioclient_mock) -> None:
    """Bekannte Einstellungen bekommen Einheit und Wertebereich, unbekannte sind deaktiviert."""
    mock_apis(aioclient_mock, make_beaam_config(), thing_settings={INVERTER_ID: SETTINGS})
    entry = MockConfigEntry(domain=DOMAIN, version=2, unique_id=SITE_ID, data=ENTRY_DATA)
    entry.add_to_hass(hass)
    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()
    registry = er.async_get(hass)

    def _entry(domain: str, key: str) -> er.RegistryEntry:
        entity_id = registry.async_get_entity_id(domain, DOMAIN, f"{INVERTER_ID}_{key}_{domain}")
        assert entity_id is not None, key
        return registry.async_get(entity_id)

    lock_time = hass.states.get(_entry("number", "LOCK_TIME").entity_id)
    assert lock_time.state == "1800.0"
    assert lock_time.attributes["unit_of_measurement"] == "s"
    assert lock_time.attributes["device_class"] == "duration"

    threshold = hass.states.get(_entry("number", "POWER_THRESHOLD_NORMAL_OP").entity_id)
    assert threshold.attributes["unit_of_measurement"] == "W"

    energy = hass.states.get(_entry("number", "GRIID_CHARGING_ENERGY").entity_id)
    assert energy.state == "17.0"
    assert energy.attributes["unit_of_measurement"] == "kWh"

    grid_charge = _entry("switch", "BATTERY_CHARGE_FROM_GRID_ALLOWED")
    assert grid_charge.disabled_by is None
    assert grid_charge.original_name == "Allow battery charging from grid"

    assert _entry("number", "UNKNOWN_LIMIT").disabled_by is er.RegistryEntryDisabler.INTEGRATION
    assert _entry("switch", "UNKNOWN_FEATURE").disabled_by is er.RegistryEntryDisabler.INTEGRATION
    # Keine doppelte Entität für denselben Schlüssel
    assert registry.async_get_entity_id("number", DOMAIN, f"{INVERTER_ID}_UNKNOWN_FEATURE_number") is None
