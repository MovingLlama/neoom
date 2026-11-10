"""Tests für die Diagnosedaten."""

from homeassistant.components.diagnostics import REDACTED
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.neoom.const import CLOUD_API_URL, DOMAIN
from custom_components.neoom.diagnostics import async_get_config_entry_diagnostics

from .conftest import (
    BEAAM_IP,
    ENTRY_DATA,
    INVERTER_ID,
    SITE_ID,
    make_beaam_config,
    mock_apis,
)


async def test_diagnostics_redact_credentials(hass: HomeAssistant, aioclient_mock) -> None:
    """Zugangsdaten, IP, Site-ID und Seriennummern erscheinen nicht in den Diagnosedaten."""
    config = make_beaam_config()
    config["siteId"] = SITE_ID
    # Die Cloud liefert zur Site u. a. ID, Organisation, Adresse und Koordinaten (Felder wie in der echten API)
    aioclient_mock.get(
        f"{CLOUD_API_URL}/sites/{SITE_ID}",
        json={
            "id": SITE_ID,
            "name": "Familie Muster",
            "organisation_id": "org-4711",
            "address": "Musterweg 1",
            "zip": "4020",
            "city": "Linz",
            "lat": "48.1234",
            "lng": "14.5678",
            "electricity_price": 15.45,
        },
    )
    mock_apis(
        aioclient_mock,
        config,
        thing_states={
            INVERTER_ID: [
                {"dataPointId": "dp-inv-power", "key": "POWER", "value": 100},
                {"dataPointId": "dp-inv-serial", "key": "SERIAL_NUMBER", "value": "SN-12345"},
            ]
        },
    )
    entry = MockConfigEntry(domain=DOMAIN, version=2, unique_id=SITE_ID, title="Familie Muster", data=ENTRY_DATA)
    entry.add_to_hass(hass)
    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()

    diagnostics = await async_get_config_entry_diagnostics(hass, entry)

    text = str(diagnostics)
    for secret in (
        "cloud-token", "beaam-key", BEAAM_IP, SITE_ID, "SN-12345", "Familie Muster",
        "org-4711", "Musterweg", "48.1234", "14.5678",
    ):
        assert secret not in text, secret
    assert diagnostics["entry"]["data"]["beaam_key"] == REDACTED
    assert diagnostics["local"]["states"]["dp-inv-power"]["value"] == 100
    assert diagnostics["cloud"]["data"]["site"]["electricity_price"] == 15.45
    assert INVERTER_ID in diagnostics["local"]["config"]["things"]
