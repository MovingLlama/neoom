"""Tests für Setup, Migration, Ingest-Bereinigung und Neuladen der Gerätestruktur."""

from unittest.mock import patch

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.neoom import async_remove_config_entry_device
from custom_components.neoom.const import (
    CONF_BEAAM_KEY,
    CONF_CLOUD_TOKEN,
    CONF_SCAN_INTERVAL_LOCAL,
    DOMAIN,
)

from .conftest import (
    ENTRY_DATA,
    GENERIC_ID,
    INVERTER_ID,
    SITE_ID,
    get_device,
    make_beaam_config,
    mock_apis,
)


async def _setup(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    entry.add_to_hass(hass)
    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()


async def test_migration_moves_credentials_to_data(hass: HomeAssistant, aioclient_mock) -> None:
    """Version 1: Zugangsdaten aus options wandern nach data und werden genutzt."""
    mock_apis(aioclient_mock, make_beaam_config())
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=1,
        unique_id=SITE_ID,
        data={**ENTRY_DATA, CONF_BEAAM_KEY: "old-key"},
        options={CONF_BEAAM_KEY: "options-key", CONF_SCAN_INTERVAL_LOCAL: 20},
    )
    await _setup(hass, entry)

    assert entry.state is ConfigEntryState.LOADED
    assert entry.version == 2
    assert entry.data[CONF_BEAAM_KEY] == "options-key"
    assert CONF_BEAAM_KEY not in entry.options
    assert entry.options[CONF_SCAN_INTERVAL_LOCAL] == 20
    assert entry.runtime_data.local.key == "options-key"


async def test_setup_ignores_credentials_in_options(hass: HomeAssistant, aioclient_mock) -> None:
    """Version 2: Nur entry.data zählt (Reauth/Reconfigure schreiben dorthin)."""
    mock_apis(aioclient_mock, make_beaam_config())
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=2,
        unique_id=SITE_ID,
        data={**ENTRY_DATA, CONF_BEAAM_KEY: "reauth-key"},
        options={CONF_BEAAM_KEY: "stale-key", CONF_CLOUD_TOKEN: "stale-token"},
    )
    await _setup(hass, entry)

    coordinators = entry.runtime_data
    assert coordinators.local.key == "reauth-key"
    assert coordinators.cloud.token == ENTRY_DATA[CONF_CLOUD_TOKEN]


async def test_ingest_only_for_generic_devices(hass: HomeAssistant, aioclient_mock) -> None:
    """Ingest-Entitäten nur für Generic Devices; alte deaktivierte werden entfernt, aktivierte bleiben."""
    mock_apis(aioclient_mock, make_beaam_config())
    entry = MockConfigEntry(domain=DOMAIN, version=2, unique_id=SITE_ID, data=ENTRY_DATA)
    entry.add_to_hass(hass)

    registry = er.async_get(hass)
    stale = registry.async_get_or_create(
        "number", DOMAIN, f"{INVERTER_ID}_old-dp_ingest",
        config_entry=entry, disabled_by=er.RegistryEntryDisabler.INTEGRATION,
    )
    enabled = registry.async_get_or_create(
        "number", DOMAIN, f"{INVERTER_ID}_dp-inv-power_ingest", config_entry=entry,
    )

    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()

    assert registry.async_get(stale.entity_id) is None
    # Vom Benutzer aktivierte Ingest-Entität bleibt erhalten und wird weiter bereitgestellt
    assert registry.async_get(enabled.entity_id) is not None
    assert hass.states.get(enabled.entity_id) is not None
    # Generic Device bekommt seine Ingest-Entität
    assert registry.async_get_entity_id("number", DOMAIN, f"{GENERIC_ID}_dp-gen-power_ingest")


async def test_ingest_not_created_for_regular_devices(hass: HomeAssistant, aioclient_mock) -> None:
    """Für normale Geräte werden keine neuen Ingest-Entitäten angelegt."""
    mock_apis(aioclient_mock, make_beaam_config())
    entry = MockConfigEntry(domain=DOMAIN, version=2, unique_id=SITE_ID, data=ENTRY_DATA)
    await _setup(hass, entry)

    registry = er.async_get(hass)
    assert registry.async_get_entity_id("number", DOMAIN, f"{INVERTER_ID}_dp-inv-power_ingest") is None


async def test_config_reloaded_periodically(hass: HomeAssistant, aioclient_mock) -> None:
    """Neue Geräte erscheinen nach Ablauf des Refresh-Intervalls ohne Reload."""
    mock_apis(aioclient_mock, make_beaam_config())
    entry = MockConfigEntry(domain=DOMAIN, version=2, unique_id=SITE_ID, data=ENTRY_DATA)
    await _setup(hass, entry)

    new_thing = {
        "generic-2": {
            "type": "GENERIC_METER",
            "name": "Neuer Zähler",
            "dataPoints": {
                "dp-new": {"key": "POWER", "dataType": "NUMBER", "unitOfMeasure": "W", "controllable": False}
            },
        }
    }
    aioclient_mock.clear_requests()
    mock_apis(aioclient_mock, make_beaam_config(new_thing))

    local = entry.runtime_data.local
    # Vor Ablauf des Intervalls wird die Struktur nicht neu geladen
    await local.async_refresh()
    await hass.async_block_till_done()
    assert "generic-2" not in local.beaam_config["things"]

    # Refresh-Intervall als abgelaufen markieren
    local._config_refresh_due = 0.0
    await local.async_refresh()
    await hass.async_block_till_done()

    assert "generic-2" in local.beaam_config["things"]
    registry = er.async_get(hass)
    assert registry.async_get_entity_id("number", DOMAIN, "generic-2_dp-new_ingest")


async def test_config_reload_failure_keeps_old_config(hass: HomeAssistant, aioclient_mock) -> None:
    """Schlägt das Neuladen fehl, bleibt die alte Struktur erhalten."""
    mock_apis(aioclient_mock, make_beaam_config())
    entry = MockConfigEntry(domain=DOMAIN, version=2, unique_id=SITE_ID, data=ENTRY_DATA)
    await _setup(hass, entry)
    local = entry.runtime_data.local
    old_config = local.beaam_config

    local._config_refresh_due = 0.0
    with patch.object(local, "_fetch_config", side_effect=TimeoutError):
        await local.async_refresh()

    assert local.last_update_success
    assert local.beaam_config is old_config
    # Nächster Versuch erst nach CONFIG_RETRY_INTERVAL, nicht in jedem Zyklus
    assert local._config_refresh_due > 0


async def test_remove_stale_device(hass: HomeAssistant, aioclient_mock) -> None:
    """Nur Geräte, die das Gateway nicht mehr meldet, dürfen gelöscht werden."""
    mock_apis(aioclient_mock, make_beaam_config())
    entry = MockConfigEntry(domain=DOMAIN, version=2, unique_id=SITE_ID, data=ENTRY_DATA)
    await _setup(hass, entry)

    device_registry = dr.async_get(hass)
    known = get_device(hass, (DOMAIN, GENERIC_ID), entry.entry_id)
    gateway = get_device(hass, (DOMAIN, f"beaam_{SITE_ID}"), entry.entry_id)
    gone = device_registry.async_get_or_create(
        config_entry_id=entry.entry_id, identifiers={(DOMAIN, "removed-thing")}
    )

    assert not await async_remove_config_entry_device(hass, entry, known)
    assert not await async_remove_config_entry_device(hass, entry, gateway)
    assert await async_remove_config_entry_device(hass, entry, gone)


async def test_unchanged_version_keeps_config(hass: HomeAssistant, aioclient_mock) -> None:
    """Gleicher versionTimestamp: Die bisherige Konfiguration bleibt in Gebrauch."""
    config = make_beaam_config()
    config["versionTimestamp"] = 1721051934
    mock_apis(aioclient_mock, config)
    entry = MockConfigEntry(domain=DOMAIN, version=2, unique_id=SITE_ID, data=ENTRY_DATA)
    await _setup(hass, entry)
    local = entry.runtime_data.local
    old_config = local.beaam_config

    local._config_refresh_due = 0.0
    await local.async_refresh()
    assert local.beaam_config is old_config

    # Neuer versionTimestamp: Die Konfiguration wird ersetzt
    changed = make_beaam_config()
    changed["versionTimestamp"] = 1721051999
    aioclient_mock.clear_requests()
    mock_apis(aioclient_mock, changed)
    local._config_refresh_due = 0.0
    await local.async_refresh()
    assert local.beaam_config["versionTimestamp"] == 1721051999
