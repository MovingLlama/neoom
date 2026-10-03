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
LOCAL_URL = f"http://{BEAAM_IP}/api/v1"

ENTRY_DATA = {
    CONF_CLOUD_TOKEN: "cloud-token",
    CONF_BEAAM_IP: BEAAM_IP,
    CONF_BEAAM_KEY: "beaam-key",
    CONF_SITE_ID: SITE_ID,
}

INVERTER_ID = "inverter-1"
GENERIC_ID = "generic-1"


def make_beaam_config(extra_things: dict | None = None) -> dict:
    """Erzeugt eine minimale BEAAM-Gerätestruktur."""
    things = {
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


def mock_apis(aioclient_mock, beaam_config: dict) -> None:
    """Registriert Antworten für Cloud- und lokale API."""
    aioclient_mock.get(f"{CLOUD_API_URL}/sites/{SITE_ID}", json={"electricity_price": 0.2})
    aioclient_mock.get(
        f"{CLOUD_API_URL}/sites/{SITE_ID}/energy-flow/latest", json={"gateways_online_state": "ONLINE"}
    )
    aioclient_mock.get(f"{LOCAL_URL}/site/configuration", json=beaam_config)
    aioclient_mock.get(f"{LOCAL_URL}/site/state", json={"energyFlow": {"states": []}})
    for thing_id in beaam_config["things"]:
        aioclient_mock.get(
            f"{LOCAL_URL}/things/{thing_id}/states",
            json={"states": [{"dataPointId": f"dp-{thing_id}", "key": "POWER", "value": 100}]},
        )
        aioclient_mock.get(f"{LOCAL_URL}/things/{thing_id}/settings", json={"settings": []})


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Aktiviert custom_components für alle Tests."""
    yield
