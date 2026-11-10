"""Tests für die Sensor-Plattform (Geräteklassen und Energiefluss-Werte)."""

import pytest
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.neoom.const import CLOUD_API_URL, DOMAIN

from .conftest import (
    BEAAM_IP,
    ENTRY_DATA,
    INVERTER_ID,
    SITE_ID,
    get_device,
    make_beaam_config,
    mock_apis,
)

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


CLASS_THING = {
    "hp-1": {
        "type": "HEAT_PUMP",
        "name": "Wärmepumpe",
        "dataPoints": {
            "dp-cell-no": {"key": "MAX_CELL_TEMPERATURE_NUMBER", "dataType": "NUMBER", "unitOfMeasure": "None"},
            "dp-start": {"key": "CHARGING_PROCESS_START_TIME", "dataType": "STRING", "unitOfMeasure": "None"},
            "dp-flow": {"key": "FLOW_TEMPERATURE", "dataType": "NUMBER", "unitOfMeasure": "°C"},
            "dp-time": {"key": "CHARGING_TIME", "dataType": "NUMBER", "unitOfMeasure": "s"},
            "dp-reactive": {"key": "REACTIVE_POWER", "dataType": "NUMBER", "unitOfMeasure": "VAr"},
            "dp-apparent": {"key": "APPARENT_POWER", "dataType": "NUMBER", "unitOfMeasure": "VA"},
            "dp-pressure": {"key": "PRESSURE", "dataType": "NUMBER", "unitOfMeasure": "Pa"},
        },
    }
}


async def test_device_class_follows_unit_not_key(hass: HomeAssistant, aioclient_mock) -> None:
    """Geräteklassen richten sich nach der Einheit; der Schlüsselname allein genügt nicht."""
    mock_apis(
        aioclient_mock,
        make_beaam_config(CLASS_THING, include_defaults=False),
        thing_states={
            "hp-1": [
                {"dataPointId": "dp-cell-no", "key": "MAX_CELL_TEMPERATURE_NUMBER", "value": 7},
                {"dataPointId": "dp-start", "key": "CHARGING_PROCESS_START_TIME", "value": "2026-11-10T08:00:00Z"},
                {"dataPointId": "dp-flow", "key": "FLOW_TEMPERATURE", "value": 35.5},
                {"dataPointId": "dp-time", "key": "CHARGING_TIME", "value": 120},
                {"dataPointId": "dp-reactive", "key": "REACTIVE_POWER", "value": 12},
                {"dataPointId": "dp-apparent", "key": "APPARENT_POWER", "value": 34},
                {"dataPointId": "dp-pressure", "key": "PRESSURE", "value": 101325},
            ]
        },
    )
    entry = MockConfigEntry(domain=DOMAIN, version=2, unique_id=SITE_ID, title="Haus", data=ENTRY_DATA)
    entry.add_to_hass(hass)
    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()

    def _state(dp_id: str):
        return hass.states.get(_entity_id(hass, f"hp-1_{dp_id}"))

    cell_no = _state("dp-cell-no")
    assert cell_no.state == "7.0"
    assert "device_class" not in cell_no.attributes

    start = _state("dp-start")
    assert start.state == "2026-11-10T08:00:00Z"
    assert "device_class" not in start.attributes
    assert "state_class" not in start.attributes

    flow = _state("dp-flow")
    assert flow.attributes["device_class"] == SensorDeviceClass.TEMPERATURE
    assert flow.attributes["unit_of_measurement"] == "°C"
    assert _state("dp-time").attributes["device_class"] == SensorDeviceClass.DURATION

    reactive = _state("dp-reactive")
    assert reactive.attributes["device_class"] == SensorDeviceClass.REACTIVE_POWER
    assert reactive.attributes["unit_of_measurement"] == "var"
    assert _state("dp-apparent").attributes["device_class"] == SensorDeviceClass.APPARENT_POWER
    assert _state("dp-pressure").attributes["device_class"] == SensorDeviceClass.PRESSURE


async def test_cloud_sensors(hass: HomeAssistant, aioclient_mock) -> None:
    """Tarife haben eine Statusklasse; CO2-Faktor, Netzanschluss und Online-Zähler kommen aus der Cloud."""
    config = make_beaam_config()
    aioclient_mock.get(
        f"{CLOUD_API_URL}/sites/{SITE_ID}",
        json={"electricity_price": 25.5, "co2_factor": 0.2},
    )
    aioclient_mock.get(
        f"{CLOUD_API_URL}/sites/{SITE_ID}/energy-flow/latest",
        json={
            "gateways_online_state": "ONLINE",
            "producers_online_count": 1,
            "producers_total_count": 2,
            "max_network_utilization": 11000,
            "total_storage_capacity": 23000,
        },
    )
    mock_apis(aioclient_mock, config)
    entry = MockConfigEntry(domain=DOMAIN, version=2, unique_id=SITE_ID, title="Haus", data=ENTRY_DATA)
    entry.add_to_hass(hass)
    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()

    price = hass.states.get(_entity_id(hass, f"{SITE_ID}_electricity_price"))
    assert price.state == "25.5"
    assert price.attributes["state_class"] == SensorStateClass.MEASUREMENT

    assert hass.states.get(_entity_id(hass, f"{SITE_ID}_co2_factor")).state == "0.2"
    grid_limit = hass.states.get(_entity_id(hass, f"{SITE_ID}_max_network_utilization"))
    assert grid_limit.state == "11000"
    assert grid_limit.attributes["device_class"] == SensorDeviceClass.POWER

    registry = er.async_get(hass)
    producers = registry.async_get(_entity_id(hass, f"{SITE_ID}_producers_online_count"))
    assert producers.disabled_by is er.RegistryEntryDisabler.INTEGRATION

    capacity = hass.states.get(_entity_id(hass, f"{SITE_ID}_total_storage_capacity"))
    assert capacity.attributes["device_class"] == SensorDeviceClass.ENERGY_STORAGE
    # Felder, die die Cloud für diese Site nicht liefert, ergeben keine Entität
    assert registry.async_get_entity_id("sensor", DOMAIN, f"{SITE_ID}_storages_max_power") is None


async def test_optional_cloud_sensor_removed_when_field_missing(hass: HomeAssistant, aioclient_mock) -> None:
    """Liefert die Cloud ein optionales Feld nicht, wird eine früher angelegte Entität entfernt."""
    mock_apis(aioclient_mock, make_beaam_config())
    entry = MockConfigEntry(domain=DOMAIN, version=2, unique_id=SITE_ID, title="Haus", data=ENTRY_DATA)
    entry.add_to_hass(hass)
    registry = er.async_get(hass)
    registry.async_get_or_create("sensor", DOMAIN, f"{SITE_ID}_co2_factor", config_entry=entry)

    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()

    assert registry.async_get_entity_id("sensor", DOMAIN, f"{SITE_ID}_co2_factor") is None
    assert registry.async_get_entity_id("sensor", DOMAIN, f"{SITE_ID}_electricity_price")


async def test_thermal_energy_is_total(hass: HomeAssistant, aioclient_mock) -> None:
    """Errechnete Wärmemengen schwanken leicht und sind daher TOTAL statt TOTAL_INCREASING."""
    thing = {
        "hp-1": {
            "type": "HEAT_PUMP",
            "dataPoints": {"dp-thermal": {"key": "THERMAL_ENERGY", "dataType": "NUMBER", "unitOfMeasure": "Wh"}},
        }
    }
    mock_apis(
        aioclient_mock,
        make_beaam_config(thing, include_defaults=False),
        thing_states={"hp-1": [{"dataPointId": "dp-thermal", "key": "THERMAL_ENERGY", "value": 1394901.38}]},
    )
    entry = MockConfigEntry(domain=DOMAIN, version=2, unique_id=SITE_ID, title="Haus", data=ENTRY_DATA)
    entry.add_to_hass(hass)
    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()

    state = hass.states.get(_entity_id(hass, "hp-1_dp-thermal"))
    assert state.attributes["state_class"] == SensorStateClass.TOTAL


async def test_read_only_setting_sensors(hass: HomeAssistant, aioclient_mock) -> None:
    """Einstellungen ohne Eingabe-Plattform erscheinen nur lesend als Sensor; EV_SELECTED ist ein Textfeld."""
    mock_apis(
        aioclient_mock,
        make_beaam_config(),
        thing_settings={
            INVERTER_ID: [
                {"key": "EV_SELECTED", "value": "ev-123"},
                {"key": "GRID_FEED_IN_PRIORITIZATION_TIMES", "value": "08:00-12:00"},
                {"key": "SOME_LABEL", "value": "abc"},
                {"key": "PRIORITY", "value": "1"},
            ]
        },
    )
    entry = MockConfigEntry(domain=DOMAIN, version=2, unique_id=SITE_ID, title="Haus", data=ENTRY_DATA)
    entry.add_to_hass(hass)
    registry = er.async_get(hass)
    # Sensor aus 1.1.8b1, den die Text-Entität ablöst
    registry.async_get_or_create("sensor", DOMAIN, f"{INVERTER_ID}_EV_SELECTED_setting", config_entry=entry)
    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()

    times = hass.states.get(_entity_id(hass, f"{INVERTER_ID}_GRID_FEED_IN_PRIORITIZATION_TIMES_setting"))
    assert times.state == "08:00-12:00"
    assert registry.async_get_entity_id("sensor", DOMAIN, f"{INVERTER_ID}_EV_SELECTED_setting") is None

    ev_id = registry.async_get_entity_id("text", DOMAIN, f"{INVERTER_ID}_EV_SELECTED_text")
    assert hass.states.get(ev_id).state == "ev-123"
    aioclient_mock.put(f"http://{BEAAM_IP}/api/v1/things/{INVERTER_ID}/settings", json={})
    await hass.services.async_call("text", "set_value", {"entity_id": ev_id, "value": "ev-456"}, blocking=True)
    puts = [call for call in aioclient_mock.mock_calls if call[0] == "PUT"]
    assert puts[0][2] == [{"key": "EV_SELECTED", "value": "ev-456"}]
    assert hass.states.get(ev_id).state == "ev-456"
    await hass.config_entries.async_unload(entry.entry_id)
    unknown = registry.async_get(_entity_id(hass, f"{INVERTER_ID}_SOME_LABEL_setting"))
    assert unknown.disabled_by is er.RegistryEntryDisabler.INTEGRATION
    # Einstellungen mit eigener Plattform bekommen keinen zusätzlichen Sensor
    assert registry.async_get_entity_id("sensor", DOMAIN, f"{INVERTER_ID}_PRIORITY_setting") is None


async def test_select_shows_value_outside_option_list(hass: HomeAssistant, aioclient_mock) -> None:
    """Meldet das Gateway einen Wert außerhalb der Optionsliste, wird er angezeigt statt „unbekannt“."""
    thing = {
        "cp-1": {
            "type": "CHARGING_POINT_AC",
            "dataPoints": {
                "dp-phase": {
                    "key": "PHASE_SWITCHING_MODE",
                    "dataType": "STRING",
                    "unitOfMeasure": "None",
                    "controllable": True,
                }
            },
        }
    }
    mock_apis(
        aioclient_mock,
        make_beaam_config(thing, include_defaults=False),
        thing_states={"cp-1": [{"dataPointId": "dp-phase", "key": "PHASE_SWITCHING_MODE", "value": "THREE_PHASE"}]},
    )
    entry = MockConfigEntry(domain=DOMAIN, version=2, unique_id=SITE_ID, title="Haus", data=ENTRY_DATA)
    entry.add_to_hass(hass)
    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()

    entity_id = er.async_get(hass).async_get_entity_id("select", DOMAIN, "cp-1_dp-phase_select")
    state = hass.states.get(entity_id)
    assert state.state == "three_phase"

    await entry.runtime_data.local.async_refresh()
    await hass.async_block_till_done()
    options = hass.states.get(entity_id).attributes["options"]
    assert options == ["automatic", "force_1_phase", "force_3_phase", "three_phase"]
