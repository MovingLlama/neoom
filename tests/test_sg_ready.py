"""Tests für den SG-Ready-Datenpunkt von Wärmepumpen (nur steuerbar, wenn das Gateway ihn meldet)."""

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.neoom.const import DOMAIN

from .conftest import ENTRY_DATA, SITE_ID, make_beaam_config, mock_apis

HEAT_PUMP_ID = "heat-pump-1"
VIRTUAL_DP_ID = f"{HEAT_PUMP_ID}_operating_mode_sg_ready"


def _heat_pump(datapoints: dict) -> dict:
    return {HEAT_PUMP_ID: {"type": "HEAT_PUMP", "name": "Wärmepumpe", "dataPoints": datapoints}}


async def _setup(hass: HomeAssistant, aioclient_mock, datapoints: dict, entry: MockConfigEntry | None = None) -> None:
    mock_apis(
        aioclient_mock,
        make_beaam_config(_heat_pump(datapoints), include_defaults=False),
        thing_states={HEAT_PUMP_ID: [{"key": "OPERATING_MODE_SG_READY", "value": "65636"}]},
    )
    entry = entry or MockConfigEntry(domain=DOMAIN, version=2, unique_id=SITE_ID, data=ENTRY_DATA)
    if entry.entry_id not in hass.config_entries.async_entry_ids():
        entry.add_to_hass(hass)
    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()


def _entity_id(hass: HomeAssistant, domain: str, unique_id: str) -> str | None:
    return er.async_get(hass).async_get_entity_id(domain, DOMAIN, unique_id)


async def test_virtual_sg_ready_is_read_only(hass: HomeAssistant, aioclient_mock) -> None:
    """Meldet das Gateway keinen SG-Ready-Datenpunkt, gibt es nur den Sensor, keine Auswahl."""
    await _setup(hass, aioclient_mock, {})

    sensor_id = _entity_id(hass, "sensor", f"{HEAT_PUMP_ID}_{VIRTUAL_DP_ID}")
    assert sensor_id is not None
    assert hass.states.get(sensor_id).state == "Normal (Mode 2)"
    assert _entity_id(hass, "select", f"{HEAT_PUMP_ID}_{VIRTUAL_DP_ID}_select") is None


async def test_reported_sg_ready_stays_controllable(hass: HomeAssistant, aioclient_mock) -> None:
    """Meldet das Gateway den Datenpunkt als steuerbar, bleibt die Auswahl erhalten."""
    await _setup(
        hass,
        aioclient_mock,
        {"dp-sg": {"key": "OPERATING_MODE_SG_READY", "dataType": "STRING", "controllable": True}},
    )

    select_id = _entity_id(hass, "select", f"{HEAT_PUMP_ID}_dp-sg_select")
    assert select_id is not None
    assert hass.states.get(select_id).state == "2"
    assert _entity_id(hass, "sensor", f"{HEAT_PUMP_ID}_{VIRTUAL_DP_ID}") is None


async def test_stale_virtual_sg_ready_select_removed(hass: HomeAssistant, aioclient_mock) -> None:
    """Auswahl-Entitäten früherer Versionen für den virtuellen Datenpunkt werden entfernt."""
    entry = MockConfigEntry(domain=DOMAIN, version=2, unique_id=SITE_ID, data=ENTRY_DATA)
    entry.add_to_hass(hass)
    registry = er.async_get(hass)
    stale = registry.async_get_or_create(
        "select", DOMAIN, f"{HEAT_PUMP_ID}_{VIRTUAL_DP_ID}_select", config_entry=entry
    )

    await _setup(hass, aioclient_mock, {}, entry)

    assert registry.async_get(stale.entity_id) is None
    assert _entity_id(hass, "sensor", f"{HEAT_PUMP_ID}_{VIRTUAL_DP_ID}") is not None
