"""Gemeinsame Fixtures für die neoom Tests."""

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from custom_components.neoom.const import (
    CLOUD_API_URL,
    CONF_BEAAM_IP,
    CONF_BEAAM_KEY,
    CONF_CLOUD_TOKEN,
    CONF_SITE_ID,
)

SITE_ID = "site-1"
BEAAM_IP = "192.0.2.10"

ENTRY_DATA = {
    CONF_CLOUD_TOKEN: "cloud-token",
    CONF_BEAAM_IP: BEAAM_IP,
    CONF_BEAAM_KEY: "beaam-key",
    CONF_SITE_ID: SITE_ID,
}

SITE_ID_2 = "site-2"
BEAAM_IP_2 = "192.0.2.20"

INVERTER_ID = "inverter-1"
GENERIC_ID = "generic-1"

# Ab HA 2026.8 gehört jedes Gerät genau einem Config-Eintrag (Abfrage pro Eintrag)
SINGLE_ENTRY_DEVICES = hasattr(dr.DeviceRegistry, "async_get_device_by_identifier")


def get_device(hass: HomeAssistant, identifier: tuple[str, str], entry_id: str) -> dr.DeviceEntry | None:
    """Sucht ein Gerät über seine Kennung, passend zur HA-Version."""
    registry = dr.async_get(hass)
    if SINGLE_ENTRY_DEVICES:
        return registry.async_get_device_by_identifier(identifier, entry_id)
    return registry.async_get_device(identifiers={identifier})


def device_entry_ids(device: dr.DeviceEntry) -> set[str]:
    """Config-Einträge eines Geräts, passend zur HA-Version."""
    if SINGLE_ENTRY_DEVICES:
        return {device.config_entry_id}
    return device.config_entries


def make_beaam_config(extra_things: dict | None = None, include_defaults: bool = True) -> dict:
    """Erzeugt eine minimale BEAAM-Gerätestruktur."""
    things = {} if not include_defaults else {
        INVERTER_ID: {
            "type": "INVERTER",
            "name": "Wechselrichter",
            "dataPoints": {
                "dp-inv-power": {
                    "key": "POWER",
                    "dataType": "NUMBER",
                    "unitOfMeasure": "W",
                    "controllable": False,
                },
            },
        },
        GENERIC_ID: {
            "type": "GENERIC_METER",
            "name": "Fremdzähler",
            "dataPoints": {
                "dp-gen-power": {
                    "key": "POWER",
                    "dataType": "NUMBER",
                    "unitOfMeasure": "W",
                    "controllable": False,
                },
            },
        },
    }
    things.update(extra_things or {})
    return {"things": things, "siteInfo": {}}


def mock_apis(
    aioclient_mock,
    beaam_config: dict,
    site_id: str = SITE_ID,
    beaam_ip: str = BEAAM_IP,
    energy_flow_states: list | None = None,
    thing_states: dict | None = None,
    thing_settings: dict | None = None,
) -> None:
    """Registriert Antworten für Cloud- und lokale API einer Site."""
    thing_states = thing_states or {}
    thing_settings = thing_settings or {}
    local_url = f"http://{beaam_ip}/api/v1"
    aioclient_mock.get(f"{CLOUD_API_URL}/sites/{site_id}", json={"electricity_price": 0.2})
    aioclient_mock.get(
        f"{CLOUD_API_URL}/sites/{site_id}/energy-flow/latest", json={"gateways_online_state": "ONLINE"}
    )
    aioclient_mock.get(f"{local_url}/site/configuration", json=beaam_config)
    aioclient_mock.get(f"{local_url}/site/state", json={"energyFlow": {"states": energy_flow_states or []}})
    for thing_id in beaam_config["things"]:
        aioclient_mock.get(
            f"{local_url}/things/{thing_id}/states",
            json={
                "states": thing_states.get(
                    thing_id, [{"dataPointId": f"dp-{thing_id}", "key": "POWER", "value": 100}]
                )
            },
        )
        aioclient_mock.get(
            f"{local_url}/things/{thing_id}/settings", json={"settings": thing_settings.get(thing_id, [])}
        )


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Aktiviert custom_components für alle Tests."""
    yield
