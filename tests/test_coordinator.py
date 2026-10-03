"""Tests für das Senden von Einstellungen und Befehlen an das BEAAM Gateway."""

from datetime import timedelta
from unittest.mock import AsyncMock, patch

import pytest
from aiohttp import ClientResponseError
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from custom_components.neoom.const import DOMAIN, SETTING_REFRESH_DELAY
from custom_components.neoom.coordinator import NeoomLocalCoordinator

from .conftest import (
    BEAAM_IP,
    ENTRY_DATA,
    INVERTER_ID,
    SITE_ID,
    make_beaam_config,
    mock_apis,
)

THING_URL = f"http://{BEAAM_IP}/api/v1/things/{INVERTER_ID}"


async def _setup(hass: HomeAssistant, aioclient_mock) -> tuple[MockConfigEntry, NeoomLocalCoordinator]:
    mock_apis(aioclient_mock, make_beaam_config())
    entry = MockConfigEntry(domain=DOMAIN, version=2, unique_id=SITE_ID, data=ENTRY_DATA)
    entry.add_to_hass(hass)
    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()
    return entry, hass.data[DOMAIN][entry.entry_id]["local"]


def _fire_after_delay(hass: HomeAssistant) -> None:
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=SETTING_REFRESH_DELAY + 0.1))


async def test_send_setting_refreshes_in_background(hass: HomeAssistant, aioclient_mock) -> None:
    """Die Einstellung kehrt nach dem PUT zurück; der Refresh folgt zeitversetzt und nur einmal."""
    _, local = await _setup(hass, aioclient_mock)
    aioclient_mock.put(f"{THING_URL}/settings", json={})

    with patch.object(local, "async_request_refresh", AsyncMock()) as refresh:
        await local.async_send_setting(INVERTER_ID, "MAX_POWER", 5000)
        await local.async_send_setting(INVERTER_ID, "MAX_POWER", 6000)

        assert local.data["settings"][INVERTER_ID]["MAX_POWER"] == "6000"
        refresh.assert_not_awaited()

        _fire_after_delay(hass)
        await hass.async_block_till_done()
        refresh.assert_awaited_once()


async def test_send_setting_error_skips_refresh(hass: HomeAssistant, aioclient_mock) -> None:
    """Lehnt das Gateway die Einstellung ab, wird der Fehler gemeldet und kein Refresh geplant."""
    _, local = await _setup(hass, aioclient_mock)
    aioclient_mock.put(f"{THING_URL}/settings", status=400)

    with patch.object(local, "async_request_refresh", AsyncMock()) as refresh:
        with pytest.raises(ClientResponseError):
            await local.async_send_setting(INVERTER_ID, "MAX_POWER", 5000)

        _fire_after_delay(hass)
        await hass.async_block_till_done()
        refresh.assert_not_awaited()


async def test_unload_cancels_pending_setting_refresh(hass: HomeAssistant, aioclient_mock) -> None:
    """Ein noch geplanter Refresh läuft nach dem Entladen nicht mehr."""
    entry, local = await _setup(hass, aioclient_mock)
    aioclient_mock.put(f"{THING_URL}/settings", json={})

    with patch.object(local, "async_request_refresh", AsyncMock()) as refresh:
        await local.async_send_setting(INVERTER_ID, "MAX_POWER", 5000)
        assert await hass.config_entries.async_unload(entry.entry_id)

        _fire_after_delay(hass)
        await hass.async_block_till_done()
        refresh.assert_not_awaited()


@pytest.mark.parametrize(
    ("endpoint", "send"),
    [
        ("commands", lambda local: local.async_send_command(INVERTER_ID, "MODE", "AUTO")),
        ("states", lambda local: local.async_ingest_state(INVERTER_ID, "POWER", 100)),
    ],
)
async def test_refresh_runs_outside_send_timeout(hass: HomeAssistant, aioclient_mock, endpoint, send) -> None:
    """Der Refresh nach Befehl/Ingest läuft erst nach dem 10-s-Timeout des Sendens."""
    _, local = await _setup(hass, aioclient_mock)
    aioclient_mock.post(f"{THING_URL}/{endpoint}", json={})
    order: list[str] = []

    with (
        patch("custom_components.neoom.coordinator.asyncio.timeout") as timeout,
        patch.object(local, "async_request_refresh", AsyncMock(side_effect=lambda: order.append("refresh"))),
    ):
        timeout.return_value.__aenter__ = AsyncMock()
        timeout.return_value.__aexit__ = AsyncMock(side_effect=lambda *_: order.append("timeout_end") or False)
        await send(local)

    assert order == ["timeout_end", "refresh"]
