"""Daten-Aktualisierungs-Koordinatoren (DataUpdateCoordinators) für neoom AI.

Diese Koordinatoren sind dafür verantwortlich, in regelmäßigen Abständen Daten
von den jeweiligen APIs (neoom AI Cloud und lokales BEAAM Gateway) abzurufen
und diese dann den Sensoren und anderen Entitäten in Home Assistant zur Verfügung zu stellen.
Das verhindert, dass jede Entität eigene Netzwerk-Anfragen stellt, was die Systeme überlasten würde.
"""

import asyncio
import time
from datetime import timedelta
from typing import Any

import aiohttp
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import (
    CLOUD_API_URL,
    CONFIG_REFRESH_INTERVAL,
    CONFIG_RETRY_INTERVAL,
    DEFAULT_SCAN_INTERVAL_CLOUD,
    DEFAULT_SCAN_INTERVAL_LOCAL,
    DOMAIN,
    LOGGER,
    SETTING_REFRESH_DELAY,
)
from .helpers import (
    SUPPORTS_VIA_DEVICE_ID,
    gateway_identifier,
    get_friendly_thing_name,
    virtual_sg_ready_dp_id,
)


class ThingFetchError(Exception):
    """Das Gateway hat die Abfrage eines Things nicht mit HTTP 200 beantwortet."""


class NeoomCloudCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Koordinator für den Abruf von Daten aus der neoom AI Cloud."""

    def __init__(
        self,
        hass: HomeAssistant,
        token: str,
        site_id: str,
        scan_interval: int = DEFAULT_SCAN_INTERVAL_CLOUD,
    ) -> None:
        """Initialisiert den Cloud-Koordinator.

        Args:
            hass: Die Home Assistant Instanz.
            token: Das Authentifizierungs-Token (Bearer Token) für die Cloud.
            site_id: Die eindeutige ID des Standorts (Site).
            scan_interval: Aktualisierungsintervall in Sekunden.
        """
        super().__init__(
            hass,
            LOGGER,
            name=f"{DOMAIN}_cloud",
            # Aktualisierungsintervall für Cloud-Daten (seltenere Änderungen wie Tarife)
            update_interval=timedelta(seconds=scan_interval),
        )
        self.token = token
        self.site_id = site_id
        # ClientSession wird von Home Assistant zentral verwaltet
        self.session = async_get_clientsession(hass)

    async def _async_update_data(self) -> dict[str, Any]:
        """Ruft die neuesten Daten von der neoom AI Cloud ab.

        Wird vom DataUpdateCoordinator in den konfigurierten Intervallen (DEFAULT_SCAN_INTERVAL_CLOUD) aufgerufen.

        Returns:
            Ein Dictionary mit den gesammelten Daten (z.B. 'site' und 'flow').

        Raises:
            UpdateFailed: Wenn beim Abruf der Daten ein Netzwerkfehler aufgetreten ist.
            ConfigEntryAuthFailed: Wenn das Token ungültig ist (Status 401).
        """
        try:
            # Setze ein asynchrones Timeout von 10 Sekunden für alle Cloud-Anfragen,
            # um zu verhindern, dass die Update-Schleife blockiert wird, wenn die Server langsam antworten.
            async with asyncio.timeout(10):
                headers = {"Authorization": f"Bearer {self.token}"}

                # 1. Allgemeine Site-Informationen abrufen (enthält u.a. Tarife, Adressen, etc.)
                url_site = f"{CLOUD_API_URL}/sites/{self.site_id}"
                async with self.session.get(url_site, headers=headers) as resp:
                    if resp.status == 401:
                        # Ein 401-Fehler deutet auf ein ungültiges Token hin.
                        # Wir werfen ConfigEntryAuthFailed, damit HA den Benutzer zur erneuten Anmeldung auffordert.
                        raise ConfigEntryAuthFailed("neoom AI Cloud Token ist ungültig oder abgelaufen.")

                    # Bei anderen HTTP-Fehlern (4xx, 5xx) wirft raise_for_status eine Exception.
                    resp.raise_for_status()
                    site_data: dict[str, Any] = await resp.json()

                # 2. Den letzten Energiefluss abrufen (aktuelle Übersichtswerte wie Gesamtverbrauch etc.)
                url_flow = f"{CLOUD_API_URL}/sites/{self.site_id}/energy-flow/latest"
                async with self.session.get(url_flow, headers=headers) as resp:
                    if resp.status == 401:
                        raise ConfigEntryAuthFailed("neoom AI Cloud Token ist ungültig oder abgelaufen.")
                    resp.raise_for_status()
                    flow_data: dict[str, Any] = await resp.json()

            # Wir bündeln beide API-Antworten in einem einzigen Dictionary,
            # das dann unseren Entitäten über `coordinator.data` zur Verfügung steht.
            return {
                "site": site_data,
                "flow": flow_data
            }

        except ConfigEntryAuthFailed:
            raise
        except aiohttp.ClientError as err:
            # Fängt alle Fehler ab, die während der HTTP-Kommunikation auftreten
            # (z.B. Verbindungsabbrüche, DNS-Probleme).
            raise UpdateFailed(f"Fehler bei der Kommunikation mit der neoom AI API: {err}") from err
        except TimeoutError as err:
            # Fängt Überschreitungen des asyncio.timeout ab
            raise UpdateFailed("Timeout bei der Verbindung zur neoom AI API.") from err

    async def close(self) -> None:
        """Schließen-Methode (Session wird von Home Assistant verwaltet)."""


class NeoomLocalCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Koordinator für den Abruf von lokalen Live-Daten vom BEAAM Gateway."""

    def __init__(
        self,
        hass: HomeAssistant,
        ip: str,
        key: str,
        site_id: str,
        scan_interval: int = DEFAULT_SCAN_INTERVAL_LOCAL,
    ) -> None:
        """Initialisiert den lokalen Koordinator.

        Args:
            hass: Die Home Assistant Instanz.
            ip: Die IP-Adresse des lokalen BEAAM Gateways.
            site_id: Die Site, zu der dieses Gateway gehört.
            key: Der Local-API-Key für die Authentifizierung.
            scan_interval: Aktualisierungsintervall in Sekunden.
        """
        super().__init__(
            hass,
            LOGGER,
            name=f"{DOMAIN}_local",
            # Häufigeres Update-Intervall für echtzeitnahe Energiedaten.
            update_interval=timedelta(seconds=scan_interval),
        )
        self.ip = ip
        self.key = key
        # Geräte-Kennung des Gateways; alle Things hängen über gateway_link daran
        self.gateway_identifier = gateway_identifier(site_id)
        # Registry-ID des Gateway-Geräts, wird beim Setup in __init__.py gesetzt
        self.gateway_device_id: str | None = None
        # Things, deren letzte Abfrage fehlgeschlagen ist (für einmalige Warnung/Erholungsmeldung)
        self._unreachable_things: set[str] = set()
        # Geplanter Refresh nach einer Einstellungsänderung (zum Abbrechen beim Entladen)
        self._unsub_setting_refresh: CALLBACK_TYPE | None = None
        self.session = async_get_clientsession(hass)

        # Speichert die Konfiguration des Gateways. Die Struktur der angebundenen Geräte
        # (Wechselrichter, Speicher) ändert sich selten und wird daher nur alle
        # CONFIG_REFRESH_INTERVAL Sekunden neu geladen, nicht bei jedem Zyklus.
        self.beaam_config: dict[str, Any] | None = None
        # Zeitpunkt (time.monotonic), ab dem die Konfiguration neu geladen werden soll.
        self._config_refresh_due: float = 0.0

    @property
    def gateway_link(self) -> dict[str, Any]:
        """DeviceInfo-Felder, die ein Thing mit dem BEAAM Gateway verknüpfen."""
        if SUPPORTS_VIA_DEVICE_ID and self.gateway_device_id:
            return {"via_device_id": self.gateway_device_id}
        return {"via_device": self.gateway_identifier}

    async def _ensure_config_loaded(self) -> None:
        """Stellt sicher, dass die Gerätestruktur ("Konfiguration") vom Gateway geladen und aktuell ist.

        Diese Konfiguration enhält Informationen über alle verbundenden Geräte ("Things")
        und ihre verfügbaren Datenpunkte ("DataPoints").
        Die API wird beim ersten Aufruf und danach alle CONFIG_REFRESH_INTERVAL Sekunden abgefragt,
        damit neue Geräte ohne Neustart erkannt werden. Schlägt ein erneutes Laden fehl,
        bleibt die bisherige Konfiguration erhalten.
        """
        now = time.monotonic()
        if self.beaam_config is not None and now < self._config_refresh_due:
            return  # Konfiguration ist geladen und noch aktuell

        try:
            self.beaam_config = await self._fetch_config()
            self._config_refresh_due = now + CONFIG_REFRESH_INTERVAL
        except ConfigEntryAuthFailed:
            raise
        except Exception as err:
            if self.beaam_config is None:
                # Ohne Konfiguration können keine Entitäten angelegt werden.
                raise UpdateFailed(f"Konnte BEAAM Konfiguration nicht laden: {err}") from err
            LOGGER.warning(
                "Neuladen der BEAAM Konfiguration fehlgeschlagen (%s). Verwende bisherige Konfiguration.",
                err,
            )
            self._config_refresh_due = now + CONFIG_RETRY_INTERVAL

    async def _fetch_config(self) -> dict[str, Any]:
        """Lädt die Gerätestruktur vom Gateway und ergänzt virtuelle Datenpunkte."""
        url = f"http://{self.ip}/api/v1/site/configuration"
        headers = {"Authorization": f"Bearer {self.key}"}

        # Längeres Timeout für den Konfigurationsabruf
        async with asyncio.timeout(10):
            async with self.session.get(url, headers=headers) as resp:
                if resp.status == 401:
                    raise ConfigEntryAuthFailed("Lokaler BEAAM API Key ist ungültig oder abgewiesen.")

                resp.raise_for_status()
                config = await resp.json()

        # Meldet das Gateway bei einer Wärmepumpe keinen SG-Ready-Datenpunkt, wird ein virtueller
        # Datenpunkt ergänzt, damit der Modus angezeigt wird (der Wert kommt über den Schlüssel aus
        # den States). Er ist nicht steuerbar: Gesteuert wird nur, was das Gateway selbst als
        # steuerbar meldet.
        if config and "things" in config:
            for thing_id, thing_data in config["things"].items():
                if thing_data and thing_data.get("type") == "HEAT_PUMP":
                    datapoints = thing_data.setdefault("dataPoints", {})
                    sg_ready_exists = any(dp.get("key") == "OPERATING_MODE_SG_READY" for dp in datapoints.values())
                    if not sg_ready_exists:
                        datapoints[virtual_sg_ready_dp_id(thing_id)] = {
                            "key": "OPERATING_MODE_SG_READY",
                            "dataType": "STRING",
                            "unitOfMeasure": "None",
                            "controllable": False,
                            "virtual": True,
                        }
                        LOGGER.debug("Virtueller SG-Ready-Datenpunkt (nur lesend) für Wärmepumpe %s ergänzt", thing_id)

        LOGGER.debug("BEAAM Konfiguration (Gerätestruktur) erfolgreich geladen.")
        return config

    async def _fetch_thing_endpoint(self, thing_id: str, endpoint: str, headers: dict[str, str]) -> dict[str, Any]:
        """Ruft einen Endpunkt ('states' oder 'settings') eines einzelnen Geräts ('Thing') ab.

        Fehler werden geworfen und nach der Abfragerunde in _async_track_thing_errors ausgewertet.
        """
        url = f"http://{self.ip}/api/v1/things/{thing_id}/{endpoint}"
        async with asyncio.timeout(5):
            async with self.session.get(url, headers=headers) as resp:
                if endpoint == "settings" and resp.status == 404:
                    # Things ohne Einstellungen sind kein Fehler
                    return {"settings": []}
                if resp.status != 200:
                    raise ThingFetchError(f"HTTP {resp.status}")
                return await resp.json()

    async def _fetch_thing_state(self, thing_id: str, headers: dict[str, str]) -> dict[str, Any]:
        """Hilfsfunktion: Ruft den detaillierten Status eines einzelnen Geräts ('Thing') auf dem BEAAM ab."""
        return await self._fetch_thing_endpoint(thing_id, "states", headers)

    async def _fetch_thing_settings(self, thing_id: str, headers: dict[str, str]) -> dict[str, Any]:
        """Hilfsfunktion: Ruft die Einstellungen eines einzelnen Geräts ('Thing') auf dem BEAAM ab."""
        return await self._fetch_thing_endpoint(thing_id, "settings", headers)

    @callback
    def _async_track_thing_errors(self, errors: dict[str, list[str]], thing_ids: list[str]) -> None:
        """Meldet Fehler einzelner Things einmalig als Warnung und die Erholung als Info.

        Solange ein Thing nicht erreichbar ist, landen weitere Fehler nur im Debug-Log.
        """
        things = (self.beaam_config or {}).get("things", {})

        def _name(thing_id: str) -> str:
            thing = things.get(thing_id)
            thing_type = thing.get("type", "Thing") if isinstance(thing, dict) else "Thing"
            return get_friendly_thing_name(self.beaam_config or {}, thing_id, thing_type)

        for thing_id in thing_ids:
            thing_errors = errors.get(thing_id)
            if thing_errors and thing_id not in self._unreachable_things:
                self._unreachable_things.add(thing_id)
                LOGGER.warning(
                    "Gerät '%s' (%s) ist über das BEAAM Gateway nicht abrufbar: %s. "
                    "Weitere Fehler werden nur im Debug-Log protokolliert.",
                    _name(thing_id), thing_id, "; ".join(thing_errors),
                )
            elif thing_errors:
                LOGGER.debug("Gerät '%s' weiterhin nicht abrufbar: %s", thing_id, "; ".join(thing_errors))
            elif thing_id in self._unreachable_things:
                self._unreachable_things.discard(thing_id)
                LOGGER.info("Gerät '%s' (%s) ist wieder erreichbar.", _name(thing_id), thing_id)

        # Things, die das Gateway nicht mehr meldet, nicht weiter verfolgen
        self._unreachable_things.intersection_update(thing_ids)

    async def _async_update_data(self) -> dict[str, Any]:
        """Ruft die Echtzeit-Statusdaten vom BEAAM Gateway ab."""
        await self._ensure_config_loaded()

        headers = {"Authorization": f"Bearer {self.key}"}
        state_map: dict[str, Any] = {}
        settings_map: dict[str, dict[str, Any]] = {}

        try:
            async with asyncio.timeout(20):
                # 1. Globalen Site-Status abrufen
                url_site = f"http://{self.ip}/api/v1/site/state"
                try:
                    async with self.session.get(url_site, headers=headers) as resp:
                        if resp.status == 401:
                            raise ConfigEntryAuthFailed("Lokaler BEAAM API Key ist ungültig.")
                        resp.raise_for_status()
                        site_data: dict[str, Any] = await resp.json()

                        if isinstance(site_data, dict) and "energyFlow" in site_data:
                            energy_flow = site_data.get("energyFlow")
                            if isinstance(energy_flow, dict) and "states" in energy_flow:
                                states_list = energy_flow.get("states")
                                if isinstance(states_list, list):
                                    for item in states_list:
                                        if isinstance(item, dict):
                                            dp_id = item.get("dataPointId")
                                            key = item.get("key")
                                            if dp_id is not None:
                                                state_map[str(dp_id)] = item
                                            if key is not None:
                                                state_map[f"energyFlow_{key}"] = item
                except ConfigEntryAuthFailed:
                    raise
                except Exception as err:
                    LOGGER.warning("Fehler beim Abrufen des globalen Site-Status (site/state): %s. Versuche dennoch, den Status der einzelnen Geräte abzurufen.", err)

                # 2. Detail-Status und Einstellungen für einzelne Geräte ("Things") abrufen
                if self.beaam_config and "things" in self.beaam_config and isinstance(self.beaam_config["things"], dict):
                    thing_ids = list(self.beaam_config["things"].keys())

                    if thing_ids:
                        coros_states = [self._fetch_thing_state(tid, headers) for tid in thing_ids]
                        coros_settings = [self._fetch_thing_settings(tid, headers) for tid in thing_ids]

                        # States und Settings in einer Runde parallel abfragen, dann wieder aufteilen
                        results = await asyncio.gather(*coros_states, *coros_settings, return_exceptions=True)
                        results_states = results[: len(thing_ids)]
                        results_settings = results[len(thing_ids) :]

                        errors: dict[str, list[str]] = {}
                        for endpoint, endpoint_results in (("states", results_states), ("settings", results_settings)):
                            for thing_id, res in zip(thing_ids, endpoint_results, strict=False):
                                if isinstance(res, BaseException):
                                    reason = str(res) or type(res).__name__
                                    errors.setdefault(thing_id, []).append(f"{endpoint}: {reason}")
                        self._async_track_thing_errors(errors, thing_ids)

                        for thing_id, res in zip(thing_ids, results_states, strict=False):
                            if isinstance(res, dict) and "states" in res:
                                states_list = res.get("states")
                                if isinstance(states_list, list):
                                    for item in states_list:
                                        if isinstance(item, dict):
                                            dp_id = item.get("dataPointId")
                                            key = item.get("key")
                                            if dp_id is not None:
                                                state_map[str(dp_id)] = item
                                            if key is not None:
                                                state_map[f"{thing_id}_{key}"] = item

                        for thing_id, res in zip(thing_ids, results_settings, strict=False):
                            if isinstance(res, dict) and "settings" in res:
                                settings_list = res.get("settings")
                                if isinstance(settings_list, list):
                                    settings_map[thing_id] = {
                                        s["key"]: s["value"]
                                        for s in settings_list
                                        if isinstance(s, dict) and s.get("key") is not None and "value" in s
                                    }

                return {
                    "config": self.beaam_config,
                    "states": state_map,
                    "settings": settings_map
                }

        except ConfigEntryAuthFailed:
            raise
        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Kommunikationsfehler (Netzwerk/HTTP) mit BEAAM Gateway: {err}") from err
        except TimeoutError as err:
            raise UpdateFailed("Timeout beim Erfassen lokaler Daten via BEAAM.") from err


    async def async_send_command(self, thing_id: str, key: str, value: Any) -> None:
        """Sendet einen Steuerungsbefehl an die BEAAM API."""
        url = f"http://{self.ip}/api/v1/things/{thing_id}/commands"
        headers = {
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json"
        }

        payload = [
            {
                "key": key,
                "value": value
            }
        ]

        LOGGER.debug("Sende Befehl an lokales BEAAM Gerät '%s': '%s' = '%s'", thing_id, key, value)

        try:
            async with asyncio.timeout(10):
                async with self.session.post(url, headers=headers, json=payload) as resp:
                    resp.raise_for_status()
                    LOGGER.info("Befehl an BEAAM erfolgreich gesendet: %s -> %s", key, value)
        except Exception as err:
            LOGGER.error("Schwerwiegender Fehler beim Senden des Befehls an '%s': %s", thing_id, err)
            raise

        # Außerhalb des Timeouts: Ein langsamer Refresh macht den gesendeten Befehl nicht ungültig
        await self.async_request_refresh()

    async def async_ingest_state(self, thing_id: str, key: str, value: Any) -> None:
        """Sendet (ingests) einen Sensorwert an ein generisches Gerät im BEAAM Gateway."""
        url = f"http://{self.ip}/api/v1/things/{thing_id}/states"
        headers = {
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json"
        }

        payload = [
            {
                "key": key,
                "value": value
            }
        ]

        LOGGER.debug("Sende State-Ingest an lokales BEAAM Gerät '%s': '%s' = '%s'", thing_id, key, value)

        try:
            async with asyncio.timeout(10):
                async with self.session.post(url, headers=headers, json=payload) as resp:
                    resp.raise_for_status()
                    LOGGER.info("State-Ingest an BEAAM erfolgreich gesendet: %s -> %s", key, value)
        except Exception as err:
            LOGGER.error("Schwerwiegender Fehler beim Senden des States an '%s': %s", thing_id, err)
            raise

        # Außerhalb des Timeouts: Ein langsamer Refresh macht den gesendeten Wert nicht ungültig
        await self.async_request_refresh()

    async def async_send_setting(self, thing_id: str, key: str, value: Any) -> None:
        """Sendet eine Einstellungsänderung an die BEAAM API."""
        url = f"http://{self.ip}/api/v1/things/{thing_id}/settings"
        headers = {
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json"
        }

        api_value = value
        if isinstance(value, bool):
            api_value = "true" if value else "false"
        elif isinstance(value, (int, float)):
            api_value = str(int(value)) if value == int(value) else str(value)
        elif isinstance(value, str):
            if value.lower() == "true":
                api_value = "true"
            elif value.lower() == "false":
                api_value = "false"
            else:
                api_value = value
        else:
            api_value = str(value)

        payload = [
            {
                "key": key,
                "value": api_value
            }
        ]

        LOGGER.info("Sende Einstellung an lokales BEAAM Gerät '%s': '%s' = '%s' (Roh: %s)", thing_id, key, api_value, value)

        try:
            async with asyncio.timeout(10):
                async with self.session.put(url, headers=headers, json=payload) as resp:
                    response_text = await resp.text()
                    LOGGER.debug("BEAAM Antwort erhalten (Status: %s): %s", resp.status, response_text)
                    resp.raise_for_status()
                    LOGGER.info("Einstellung an BEAAM erfolgreich gesendet: %s -> %s", key, api_value)

                    if self.data:
                        if "settings" not in self.data:
                            self.data["settings"] = {}
                        if thing_id not in self.data["settings"]:
                            self.data["settings"][thing_id] = {}
                        self.data["settings"][thing_id][key] = api_value
        except Exception as err:
            LOGGER.error("Schwerwiegender Fehler beim Senden der Einstellung an '%s': %s", thing_id, err)
            raise

        # Die Einstellung gilt als gesetzt, sobald das Gateway sie angenommen hat. Der neue Wert
        # wird sofort angezeigt und kurz darauf im Hintergrund vom Gateway bestätigt.
        self.async_update_listeners()
        self._async_schedule_setting_refresh()

    @callback
    def _async_schedule_setting_refresh(self) -> None:
        """Plant einen Refresh SETTING_REFRESH_DELAY Sekunden nach einer Einstellungsänderung.

        Mehrere Änderungen kurz hintereinander lösen nur einen Refresh aus.
        """
        if self._unsub_setting_refresh is not None:
            self._unsub_setting_refresh()

        async def _async_refresh(_now: Any) -> None:
            self._unsub_setting_refresh = None
            await self.async_request_refresh()

        self._unsub_setting_refresh = async_call_later(self.hass, SETTING_REFRESH_DELAY, _async_refresh)

    async def close(self) -> None:
        """Bricht einen noch geplanten Refresh ab (die Session wird von Home Assistant verwaltet)."""
        if self._unsub_setting_refresh is not None:
            self._unsub_setting_refresh()
            self._unsub_setting_refresh = None
