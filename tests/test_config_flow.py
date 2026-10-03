"""Tests für Reauth, Reconfigure und Optionen-Fluss."""

from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.neoom.const import (
    CONF_BEAAM_IP,
    CONF_BEAAM_KEY,
    CONF_CLOUD_TOKEN,
    CONF_SCAN_INTERVAL_CLOUD,
    CONF_SCAN_INTERVAL_LOCAL,
    DOMAIN,
)

from .conftest import BEAAM_IP, ENTRY_DATA, SITE_ID, make_beaam_config, mock_apis


async def _loaded_entry(hass: HomeAssistant, aioclient_mock) -> MockConfigEntry:
    mock_apis(aioclient_mock, make_beaam_config())
    entry = MockConfigEntry(domain=DOMAIN, version=2, unique_id=SITE_ID, data=ENTRY_DATA)
    entry.add_to_hass(hass)
    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()
    return entry


async def test_options_flow_stores_credentials_in_data(hass: HomeAssistant, aioclient_mock) -> None:
    """Zahnrad: Zugangsdaten nach data, nur Intervalle nach options."""
    entry = await _loaded_entry(hass, aioclient_mock)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_SCAN_INTERVAL_LOCAL: 30,
            CONF_SCAN_INTERVAL_CLOUD: 600,
            CONF_BEAAM_IP: BEAAM_IP,
            CONF_BEAAM_KEY: "new-key",
            CONF_CLOUD_TOKEN: ENTRY_DATA[CONF_CLOUD_TOKEN],
        },
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options == {CONF_SCAN_INTERVAL_LOCAL: 30, CONF_SCAN_INTERVAL_CLOUD: 600}
    assert entry.data[CONF_BEAAM_KEY] == "new-key"
    assert hass.data[DOMAIN][entry.entry_id]["local"].key == "new-key"


async def test_reauth_after_options_uses_new_credentials(hass: HomeAssistant, aioclient_mock) -> None:
    """Regression: Nach gespeicherten Optionen muss Reauth wirken."""
    entry = await _loaded_entry(hass, aioclient_mock)

    # Erst Optionen speichern (früher landeten Zugangsdaten dabei in options)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_SCAN_INTERVAL_LOCAL: 15,
            CONF_SCAN_INTERVAL_CLOUD: 300,
            CONF_BEAAM_IP: BEAAM_IP,
            CONF_BEAAM_KEY: ENTRY_DATA[CONF_BEAAM_KEY],
            CONF_CLOUD_TOKEN: ENTRY_DATA[CONF_CLOUD_TOKEN],
        },
    )
    await hass.async_block_till_done()

    result = await entry.start_reauth_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_CLOUD_TOKEN: "fresh-token",
            CONF_BEAAM_IP: BEAAM_IP,
            CONF_BEAAM_KEY: "fresh-key",
        },
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    coordinators = hass.data[DOMAIN][entry.entry_id]
    assert coordinators["local"].key == "fresh-key"
    assert coordinators["cloud"].token == "fresh-token"


async def test_reconfigure_shows_and_updates_data(hass: HomeAssistant, aioclient_mock) -> None:
    """Reconfigure zeigt die Werte aus data und schreibt dorthin."""
    entry = await _loaded_entry(hass, aioclient_mock)

    result = await entry.start_reconfigure_flow(hass)
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_CLOUD_TOKEN: ENTRY_DATA[CONF_CLOUD_TOKEN],
            CONF_BEAAM_IP: BEAAM_IP,
            CONF_BEAAM_KEY: "reconf-key",
        },
    )
    await hass.async_block_till_done()

    assert result["reason"] == "reconfigure_successful"
    assert hass.data[DOMAIN][entry.entry_id]["local"].key == "reconf-key"
