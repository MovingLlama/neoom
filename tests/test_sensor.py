"""Tests für die Sensor-Plattform (Geräteklassen und Energiefluss-Werte)."""

import pytest
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.neoom.const import DOMAIN

from .conftest import ENTRY_DATA, SITE_ID, get_device, make_beaam_config, mock_apis

BATTERY_ID = "battery-1"
BATTERY_THING = {
    BATTERY_ID: {
        "type": "ENERGY_STORAGE",
        "name": "Batterie Master",
        "dataPoints": {
            "dp-bat-soc": {
                "key": "STATE_OF_CHARGE",
                "dataType": "NUMBER",
                "unitOfMeasure": "%",
                "controllable": False,
            },
        },
    }
}
ENERGY_FLOW_CONFIG = {
    "dataPoints": {
        "dp-ef-consumption": {
            "key": "POWER_CONSUMPTION_CALC",
            "dataType": "NUMBER",
            "unitOfMeasure": "W",
        },
        "dp-ef-consumed-calc": {
            "key": "ENERGY_CONSUMED_CALC",
            "dataType": "NUMBER",
            "unitOfMeasure": "Wh",
        },
        "dp-ef-imported": {
            "key": "ENERGY_IMPORTED",
            "dataType": "NUMBER",
            "unitOfMeasure": "Wh",
        },
        "dp-ef-soc": {
            "key": "STATE_OF_CHARGE",
            "dataType": "NUMBER",
            "unitOfMeasure": "%",
        },
        "dp-ef-fraction": {
            "key": "FRACTION_PV_TO_CONSUMPTION",
            "dataType": "NUMBER",
            "unitOfMeasure": "None",
        },
        "dp-ef-power-consumption": {
            "key": "POWER_CONSUMPTION",
            "dataType": "NUMBER",
            "unitOfMeasure": "W",
        },
    }
}


async def _setup(hass: HomeAssistant, aioclient_mock) -> MockConfigEntry:
    config = make_beaam_config(BATTERY_THING, include_defaults=False)
    config["energyFlow"] = ENERGY_FLOW_CONFIG
    mock_apis(
        aioclient_mock,
        config,
        energy_flow_states=[
            {"dataPointId": "dp-ef-consumption", "key": "POWER_CONSUMPTION_CALC", "value": 1234},
            {"dataPointId": "dp-ef-soc", "key": "STATE_OF_CHARGE", "value": 55},
            {"dataPointId": "dp-ef-consumed-calc", "key": "ENERGY_CONSUMED_CALC", "value": -1562201.6},
            {"dataPointId": "dp-ef-imported", "key": "ENERGY_IMPORTED", "value": 7860942.2},
            {"dataPointId": "dp-ef-fraction", "key": "FRACTION_PV_TO_CONSUMPTION", "value": 0.706893433065356},
            {"dataPointId": "dp-ef-power-consumption", "key": "POWER_CONSUMPTION", "value": None},
        ],
        thing_states={
            BATTERY_ID: [{"dataPointId": "dp-bat-soc", "key": "STATE_OF_CHARGE", "value": 80}]
        },
    )
    entry = MockConfigEntry(domain=DOMAIN, version=2, unique_id=SITE_ID, title="Haus", data=ENTRY_DATA)
    entry.add_to_hass(hass)
    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()
    return entry


def _entity_id(hass: HomeAssistant, unique_id: str) -> str:
    entity_id = er.async_get(hass).async_get_entity_id("sensor", DOMAIN, unique_id)
    assert entity_id is not None, unique_id
    return entity_id


async def test_state_of_charge_has_battery_device_class(hass: HomeAssistant, aioclient_mock) -> None:
    """STATE_OF_CHARGE wird als Batterie-Sensor erkannt (Issue #1)."""
    await _setup(hass, aioclient_mock)

    state = hass.states.get(_entity_id(hass, f"{BATTERY_ID}_dp-bat-soc"))
    assert state.state == "80.0"
    assert state.attributes["device_class"] == SensorDeviceClass.BATTERY
    assert state.attributes["state_class"] == SensorStateClass.MEASUREMENT
    assert state.attributes["unit_of_measurement"] == "%"


async def test_energy_flow_sensors_on_gateway(hass: HomeAssistant, aioclient_mock) -> None:
    """Standortweite Energiefluss-Werte (z.B. Hausverbrauch) werden am Gateway angelegt."""
    await _setup(hass, aioclient_mock)

    consumption_id = _entity_id(hass, f"beaam_{SITE_ID}_energy_flow_dp-ef-consumption")
    state = hass.states.get(consumption_id)
    assert state.state == "1234.0"
    assert state.attributes["device_class"] == SensorDeviceClass.POWER
    assert state.attributes["unit_of_measurement"] == "W"

    soc = hass.states.get(_entity_id(hass, f"beaam_{SITE_ID}_energy_flow_dp-ef-soc"))
    assert soc.state == "55.0"
    assert soc.attributes["device_class"] == SensorDeviceClass.BATTERY

    entity = er.async_get(hass).async_get(consumption_id)
    gateway = get_device(hass, (DOMAIN, f"beaam_{SITE_ID}"), entity.config_entry_id)
    assert entity.device_id == gateway.id


async def test_derived_energy_values_use_total(hass: HomeAssistant, aioclient_mock) -> None:
    """Berechnete Bilanzen (können sinken/negativ sein) sind TOTAL, echte Zähler TOTAL_INCREASING."""
    await _setup(hass, aioclient_mock)

    calc = hass.states.get(_entity_id(hass, f"beaam_{SITE_ID}_energy_flow_dp-ef-consumed-calc"))
    assert calc.state == "-1562201.6"
    assert calc.attributes["state_class"] == SensorStateClass.TOTAL

    imported = hass.states.get(_entity_id(hass, f"beaam_{SITE_ID}_energy_flow_dp-ef-imported"))
    assert imported.attributes["state_class"] == SensorStateClass.TOTAL_INCREASING


async def test_fraction_shown_as_percentage(hass: HomeAssistant, aioclient_mock) -> None:
    """Anteile (0…1) werden in Prozent angezeigt."""
    await _setup(hass, aioclient_mock)

    state = hass.states.get(_entity_id(hass, f"beaam_{SITE_ID}_energy_flow_dp-ef-fraction"))
    assert float(state.state) == pytest.approx(70.6893433065356)
    assert state.attributes["unit_of_measurement"] == "%"
    assert state.attributes["state_class"] == SensorStateClass.MEASUREMENT


async def test_meter_only_values_disabled_by_default(hass: HomeAssistant, aioclient_mock) -> None:
    """Werte, die nur ein eigener Verbrauchszähler liefert, sind standardmäßig deaktiviert."""
    await _setup(hass, aioclient_mock)

    entity_id = _entity_id(hass, f"beaam_{SITE_ID}_energy_flow_dp-ef-power-consumption")
    assert er.async_get(hass).async_get(entity_id).disabled_by is er.RegistryEntryDisabler.INTEGRATION
    # Der berechnete Verbrauch bleibt aktiv
    calc_id = _entity_id(hass, f"beaam_{SITE_ID}_energy_flow_dp-ef-consumption")
    assert er.async_get(hass).async_get(calc_id).disabled_by is None


async def test_cloud_device_named_after_site(hass: HomeAssistant, aioclient_mock) -> None:
    """Das Cloud-Gerät trägt den Namen der Site, damit sich mehrere Sites unterscheiden."""
    entry = await _setup(hass, aioclient_mock)

    device = get_device(hass, (DOMAIN, SITE_ID), entry.entry_id)
    assert device.name == "neoom AI Cloud (Haus)"
