"""Gemeinsame Fixtures für die neoom Tests."""

import pytest

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
) -> None:
    """Registriert Antworten für Cloud- und lokale API einer Site."""
    thing_states = thing_states or {}
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
        aioclient_mock.get(f"{local_url}/things/{thing_id}/settings", json={"settings": []})


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Aktiviert custom_components für alle Tests."""
    yield
