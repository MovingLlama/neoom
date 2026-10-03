"""Tests für das BEAAM Gateway-Gerät (eine Instanz pro Site) und seine Migration."""

from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import device_registry as dr
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.neoom.const import (
    CLOUD_API_URL,
    CONF_BEAAM_IP,
    CONF_BEAAM_KEY,
    CONF_CLOUD_TOKEN,
    CONF_SITE_ID,
    DOMAIN,
)

from .conftest import (
    BEAAM_IP,
    BEAAM_IP_2,
    ENTRY_DATA,
    GENERIC_ID,
    SINGLE_ENTRY_DEVICES,
    SITE_ID,
    SITE_ID_2,
    device_entry_ids,
    get_device,
    make_beaam_config,
    mock_apis,
)

LEGACY_ID = (DOMAIN, "BEAAM Gateway")
ENTRY_DATA_2 = {**ENTRY_DATA, CONF_SITE_ID: SITE_ID_2, CONF_BEAAM_IP: BEAAM_IP_2}
SITE_2_THING = {
    "meter-2": {
        "type": "METER",
        "name": "Zähler Site 2",
        "dataPoints": {
            "dp-m2": {"key": "POWER", "dataType": "NUMBER", "unitOfMeasure": "W", "controllable": False}
        },
    }
}


def _mock_two_sites(aioclient_mock) -> None:
    mock_apis(aioclient_mock, make_beaam_config())
    mock_apis(
        aioclient_mock,
        make_beaam_config(SITE_2_THING, include_defaults=False),
        site_id=SITE_ID_2,
        beaam_ip=BEAAM_IP_2,
    )


def _thing_parent(hass: HomeAssistant, thing_id: str, entry_id: str) -> dr.DeviceEntry:
    thing = get_device(hass, (DOMAIN, thing_id), entry_id)
    return dr.async_get(hass).async_get(thing.via_device_id)


async def test_two_sites_get_separate_gateways(hass: HomeAssistant, aioclient_mock) -> None:
    """Zwei Sites in einer HA erhalten je ein eigenes Gateway-Gerät."""
    _mock_two_sites(aioclient_mock)
    entry_1 = MockConfigEntry(domain=DOMAIN, version=2, unique_id=SITE_ID, title="Haus", data=ENTRY_DATA)
    entry_2 = MockConfigEntry(domain=DOMAIN, version=2, unique_id=SITE_ID_2, title="Carport", data=ENTRY_DATA_2)
    entry_1.add_to_hass(hass)
    entry_2.add_to_hass(hass)
    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()

    gateway_1 = get_device(hass, (DOMAIN, f"beaam_{SITE_ID}"), entry_1.entry_id)
    gateway_2 = get_device(hass, (DOMAIN, f"beaam_{SITE_ID_2}"), entry_2.entry_id)

    assert gateway_1.id != gateway_2.id
    assert device_entry_ids(gateway_1) == {entry_1.entry_id}
    assert device_entry_ids(gateway_2) == {entry_2.entry_id}
    assert gateway_1.name == "BEAAM Gateway (Haus)"
    assert get_device(hass, LEGACY_ID, entry_1.entry_id) is None
    assert get_device(hass, LEGACY_ID, entry_2.entry_id) is None
    assert _thing_parent(hass, GENERIC_ID, entry_1.entry_id).id == gateway_1.id
    assert _thing_parent(hass, "meter-2", entry_2.entry_id).id == gateway_2.id


async def test_migration_keeps_single_gateway_device(hass: HomeAssistant, aioclient_mock) -> None:
    """Version 1 mit einer Site: Gerät bleibt erhalten, nur die Kennung wird getauscht."""
    mock_apis(aioclient_mock, make_beaam_config())
    entry = MockConfigEntry(domain=DOMAIN, version=1, unique_id=SITE_ID, title="Haus", data=ENTRY_DATA)
    entry.add_to_hass(hass)

    registry = dr.async_get(hass)
    legacy = registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={LEGACY_ID, (DOMAIN, f"beaam_{SITE_ID}")},
        name="BEAAM Gateway",
    )
    registry.async_update_device(legacy.id, area_id="technikraum")

    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()

    migrated = registry.async_get(legacy.id)
    assert migrated.identifiers == {(DOMAIN, f"beaam_{SITE_ID}")}
    assert migrated.area_id == "technikraum"
    assert _thing_parent(hass, GENERIC_ID, entry.entry_id).id == legacy.id


async def test_migration_splits_shared_gateway_device(hass: HomeAssistant, aioclient_mock) -> None:
    """Version 1 mit zwei Sites auf einem Gerät: Danach hat jede Site ihr eigenes Gateway."""
    _mock_two_sites(aioclient_mock)
    entry_1 = MockConfigEntry(domain=DOMAIN, version=1, unique_id=SITE_ID, title="Haus", data=ENTRY_DATA)
    entry_2 = MockConfigEntry(domain=DOMAIN, version=1, unique_id=SITE_ID_2, title="Carport", data=ENTRY_DATA_2)
    entry_1.add_to_hass(hass)
    entry_2.add_to_hass(hass)

    registry = dr.async_get(hass)
    registry.async_get_or_create(
        config_entry_id=entry_1.entry_id,
        identifiers={LEGACY_ID, (DOMAIN, f"beaam_{SITE_ID}")},
        name="BEAAM Gateway",
    )
    legacy = registry.async_get_or_create(
        config_entry_id=entry_2.entry_id,
        identifiers={LEGACY_ID, (DOMAIN, f"beaam_{SITE_ID_2}")},
        name="BEAAM Gateway",
    )
    if not SINGLE_ENTRY_DEVICES:
        # Ab HA 2026.8 entstehen hier zwei Geräte, wie nach HAs eigener Aufteilung
        assert legacy.config_entries == {entry_1.entry_id, entry_2.entry_id}

    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()

    gateway_1 = get_device(hass, (DOMAIN, f"beaam_{SITE_ID}"), entry_1.entry_id)
    gateway_2 = get_device(hass, (DOMAIN, f"beaam_{SITE_ID_2}"), entry_2.entry_id)
    assert gateway_1.id != gateway_2.id
    assert legacy.id in (gateway_1.id, gateway_2.id)
    assert device_entry_ids(gateway_1) == {entry_1.entry_id}
    assert device_entry_ids(gateway_2) == {entry_2.entry_id}
    assert gateway_1.identifiers == {(DOMAIN, f"beaam_{SITE_ID}")}
    assert gateway_2.identifiers == {(DOMAIN, f"beaam_{SITE_ID_2}")}
    assert _thing_parent(hass, GENERIC_ID, entry_1.entry_id).id == gateway_1.id
    assert _thing_parent(hass, "meter-2", entry_2.entry_id).id == gateway_2.id


def _mock_flow_apis(aioclient_mock) -> None:
    aioclient_mock.get(
        f"{CLOUD_API_URL}/sites",
        json=[{"id": SITE_ID, "name": "Haus"}, {"id": SITE_ID_2, "name": "Carport"}],
    )
    aioclient_mock.get(f"http://{BEAAM_IP_2}/api/v1/site/configuration", json=make_beaam_config())


async def test_flow_offers_only_unconfigured_sites(hass: HomeAssistant, aioclient_mock) -> None:
    """Bereits eingebundene Sites werden nicht erneut angeboten."""
    _mock_flow_apis(aioclient_mock)
    MockConfigEntry(domain=DOMAIN, version=2, unique_id=SITE_ID, data=ENTRY_DATA).add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_CLOUD_TOKEN: "t", CONF_BEAAM_IP: BEAAM_IP_2, CONF_BEAAM_KEY: "k"},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "site_selection"
    site_options = result["data_schema"].schema[CONF_SITE_ID].container
    assert set(site_options) == {SITE_ID_2}


async def test_flow_aborts_when_all_sites_configured(hass: HomeAssistant, aioclient_mock) -> None:
    """Sind alle Sites eingebunden, bricht der Flow mit Hinweis ab."""
    _mock_flow_apis(aioclient_mock)
    MockConfigEntry(domain=DOMAIN, version=2, unique_id=SITE_ID, data=ENTRY_DATA).add_to_hass(hass)
    MockConfigEntry(
        domain=DOMAIN, version=2, unique_id=SITE_ID_2, data={**ENTRY_DATA_2, CONF_BEAAM_IP: "192.0.2.99"}
    ).add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_CLOUD_TOKEN: "t", CONF_BEAAM_IP: BEAAM_IP_2, CONF_BEAAM_KEY: "k"},
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "all_sites_configured"


async def test_flow_rejects_same_beaam_twice(hass: HomeAssistant, aioclient_mock) -> None:
    """Dasselbe BEAAM Gateway (IP) kann nicht ein zweites Mal eingebunden werden."""
    _mock_flow_apis(aioclient_mock)
    MockConfigEntry(domain=DOMAIN, version=2, unique_id=SITE_ID, data=ENTRY_DATA).add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_CLOUD_TOKEN: "t", CONF_BEAAM_IP: f"http://{BEAAM_IP}/", CONF_BEAAM_KEY: "k"},
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
