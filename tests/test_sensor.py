"""Tests für die Sensor-Plattform (Geräteklassen und Energiefluss-Werte)."""

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.neoom.const import DOMAIN

from .conftest import ENTRY_DATA, SITE_ID, make_beaam_config, mock_apis

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
        "dp-ef-soc": {
            "key": "STATE_OF_CHARGE",
            "dataType": "NUMBER",
            "unitOfMeasure": "%",
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
    gateway = dr.async_get(hass).async_get_device(identifiers={(DOMAIN, f"beaam_{SITE_ID}")})
    assert entity.device_id == gateway.id
