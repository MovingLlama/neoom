"""Tests für Ja/Nein-Datenpunkte und Array-Datenpunkte (Datentypen wie im Telegraf-Plugin)."""

from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.neoom.const import DOMAIN

from .conftest import ENTRY_DATA, SITE_ID, make_beaam_config, mock_apis

BATTERY_ID = "battery-1"
PV_ID = "pv-1"
THINGS = {
    BATTERY_ID: {
        "type": "BATTERY",
        "name": "Batterie",
        "dataPoints": {
            "dp-bat-connection": {"key": "CONNECTION", "dataType": "BOOLEAN", "unitOfMeasure": "None"},
            "dp-bat-eps": {"key": "EPS_MODE_ACTIVE", "dataType": "BOOLEAN", "unitOfMeasure": "None"},
            "dp-bat-errors": {"key": "ERROR_CODES", "dataType": "STRING_ARRAY[]", "unitOfMeasure": "None"},
            "dp-bat-modes": {"key": "OPERATING_MODES", "dataType": "STRING_ARRAY[]", "unitOfMeasure": "None"},
        },
    },
    PV_ID: {
        "type": "PV",
        "name": "PV",
        "dataPoints": {
            "dp-pv-connections": {"key": "CONNECTIONS", "dataType": "BOOLEAN_ARRAY[]", "unitOfMeasure": "None"},
            "dp-pv-voltages": {"key": "VOLTAGES", "dataType": "NUMBER_ARRAY[]", "unitOfMeasure": "V"},
        },
    },
}
THING_STATES = {
    BATTERY_ID: [
        {"dataPointId": "dp-bat-connection", "key": "CONNECTION", "value": True},
        {"dataPointId": "dp-bat-eps", "key": "EPS_MODE_ACTIVE", "value": "false"},
        {"dataPointId": "dp-bat-errors", "key": "ERROR_CODES", "value": []},
        {"dataPointId": "dp-bat-modes", "key": "OPERATING_MODES", "value": ["SELF_CONSUMPTION", "BACKUP"]},
    ],
    PV_ID: [
        {"dataPointId": "dp-pv-connections", "key": "CONNECTIONS", "value": [True, False]},
        {"dataPointId": "dp-pv-voltages", "key": "VOLTAGES", "value": [231.42, 302.25]},
    ],
}


async def _setup(hass: HomeAssistant, aioclient_mock) -> None:
    mock_apis(
        aioclient_mock,
        make_beaam_config(THINGS, include_defaults=False),
        thing_states=THING_STATES,
    )
    entry = MockConfigEntry(domain=DOMAIN, version=2, unique_id=SITE_ID, title="Haus", data=ENTRY_DATA)
    entry.add_to_hass(hass)
    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()


def _state(hass: HomeAssistant, platform: str, unique_id: str):
    entity_id = er.async_get(hass).async_get_entity_id(platform, DOMAIN, unique_id)
    assert entity_id is not None, unique_id
    return hass.states.get(entity_id)


async def test_boolean_datapoints_become_binary_sensors(hass: HomeAssistant, aioclient_mock) -> None:
    """CONNECTION ist ein Konnektivitäts-Sensor, EPS_MODE_ACTIVE ein einfacher Binärsensor."""
    await _setup(hass, aioclient_mock)

    connection = _state(hass, "binary_sensor", f"{BATTERY_ID}_dp-bat-connection")
    assert connection.state == STATE_ON
    assert connection.attributes["device_class"] == BinarySensorDeviceClass.CONNECTIVITY

    eps = _state(hass, "binary_sensor", f"{BATTERY_ID}_dp-bat-eps")
    assert eps.state == STATE_OFF


async def test_boolean_array_one_sensor_per_entry(hass: HomeAssistant, aioclient_mock) -> None:
    """CONNECTIONS (pro PV-String) ergibt einen Binärsensor pro Eintrag."""
    await _setup(hass, aioclient_mock)

    assert _state(hass, "binary_sensor", f"{PV_ID}_dp-pv-connections_0").state == STATE_ON
    assert _state(hass, "binary_sensor", f"{PV_ID}_dp-pv-connections_1").state == STATE_OFF


async def test_number_array_one_sensor_per_entry(hass: HomeAssistant, aioclient_mock) -> None:
    """VOLTAGES (pro PV-String) ergibt einen Sensor pro Eintrag mit Einheit."""
    await _setup(hass, aioclient_mock)

    first = _state(hass, "sensor", f"{PV_ID}_dp-pv-voltages_0")
    assert first.state == "231.42"
    assert first.attributes["unit_of_measurement"] == "V"
    assert first.attributes["index"] == 0
    assert _state(hass, "sensor", f"{PV_ID}_dp-pv-voltages_1").state == "302.25"


async def test_string_array_joined(hass: HomeAssistant, aioclient_mock) -> None:
    """Text-Listen werden zusammengefasst; eine leere Liste zeigt "none"."""
    await _setup(hass, aioclient_mock)

    modes = _state(hass, "sensor", f"{BATTERY_ID}_dp-bat-modes")
    assert modes.state == "SELF_CONSUMPTION, BACKUP"
    assert modes.attributes["values"] == ["SELF_CONSUMPTION", "BACKUP"]

    errors = _state(hass, "sensor", f"{BATTERY_ID}_dp-bat-errors")
    assert errors.state == "none"
    assert errors.attributes["values"] == []
