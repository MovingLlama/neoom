"""Tests für das Senden von Einstellungen und Befehlen an das BEAAM Gateway."""

import asyncio
import logging
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


async def test_states_and_settings_fetched_in_one_round(hass: HomeAssistant, aioclient_mock) -> None:
    """States und Settings laufen gleichzeitig; die Ergebnisse landen beim richtigen Thing."""
    _, local = await _setup(hass, aioclient_mock)
    settings_started = asyncio.Event()
    overlapped: list[bool] = []

    async def _state(thing_id: str, _headers: dict) -> dict:
        # In zwei getrennten Runden würde keine Settings-Abfrage starten, solange States laufen
        try:
            async with asyncio.timeout(1):
                await settings_started.wait()
            overlapped.append(True)
        except TimeoutError:
            overlapped.append(False)
        return {"states": [{"dataPointId": f"dp-{thing_id}", "key": "POWER", "value": 1}]}

    async def _settings(thing_id: str, _headers: dict) -> dict:
        settings_started.set()
        return {"settings": [{"key": "MAX_POWER", "value": f"{thing_id}-max"}]}

    with (
        patch.object(local, "_fetch_thing_state", side_effect=_state),
        patch.object(local, "_fetch_thing_settings", side_effect=_settings),
    ):
        data = await local._async_update_data()

    assert overlapped and all(overlapped)
    for thing_id in local.beaam_config["things"]:
        assert data["states"][f"{thing_id}_POWER"]["value"] == 1
        assert data["settings"][thing_id] == {"MAX_POWER": f"{thing_id}-max"}


def _override(aioclient_mock, url: str, status: int) -> None:
    """Antwortet auf url mit status, alle anderen Abfragen wie gewohnt (erster Treffer gewinnt)."""
    aioclient_mock.clear_requests()
    aioclient_mock.get(url, status=status)
    mock_apis(aioclient_mock, make_beaam_config())


async def test_unreachable_thing_logged_once_and_recovery(
    hass: HomeAssistant, aioclient_mock, caplog: pytest.LogCaptureFixture
) -> None:
    """Fällt ein Thing aus, gibt es genau eine Warnung; bei Erholung eine Info."""
    _, local = await _setup(hass, aioclient_mock)
    caplog.set_level(logging.DEBUG, logger="custom_components.neoom")

    _override(aioclient_mock, f"{THING_URL}/states", 500)
    await local._async_update_data()
    await local._async_update_data()
    warnings = [r for r in caplog.records if r.levelno == logging.WARNING and INVERTER_ID in r.getMessage()]
    assert len(warnings) == 1
    assert "states: HTTP 500" in warnings[0].getMessage()

    caplog.clear()
    aioclient_mock.clear_requests()
    mock_apis(aioclient_mock, make_beaam_config())
    data = await local._async_update_data()
    assert f"{INVERTER_ID}_POWER" in data["states"]
    infos = [r for r in caplog.records if r.levelno == logging.INFO and "wieder erreichbar" in r.getMessage()]
    assert len(infos) == 1
    assert INVERTER_ID in infos[0].getMessage()


async def test_settings_404_is_not_an_error(
    hass: HomeAssistant, aioclient_mock, caplog: pytest.LogCaptureFixture
) -> None:
    """Things ohne Einstellungen (404 auf /settings) erzeugen keine Warnung."""
    _, local = await _setup(hass, aioclient_mock)
    _override(aioclient_mock, f"{THING_URL}/settings", 404)

    data = await local._async_update_data()

    assert data["settings"][INVERTER_ID] == {}
    assert not [r for r in caplog.records if r.levelno >= logging.WARNING and r.name.startswith("custom_components.neoom")]
