"""Diagnosedaten für neoom AI.

Home Assistant bietet sie unter "Diagnosedaten herunterladen" an. Zugangsdaten,
IP-Adresse, Site-ID, Standortangaben und Gerätekennungen (Seriennummern, RFID-Karten)
werden unkenntlich gemacht, damit die Datei in einem Issue geteilt werden kann.
"""

from typing import Any

from homeassistant.components.diagnostics import REDACTED, async_redact_data
from homeassistant.core import HomeAssistant

from .const import CONF_BEAAM_IP, CONF_BEAAM_KEY, CONF_CLOUD_TOKEN, CONF_SITE_ID
from .coordinator import NeoomConfigEntry

# Schlüssel in Eintragsdaten und API-Antworten, deren Werte entfernt werden.
TO_REDACT: set[str] = {
    CONF_BEAAM_IP,
    CONF_BEAAM_KEY,
    CONF_CLOUD_TOKEN,
    CONF_SITE_ID,
    "siteId",
    "title",
    "unique_id",
    "address",
    "street",
    "zip",
    "zipCode",
    "postalCode",
    "city",
    "latitude",
    "longitude",
    "lat",
    "lng",
    "location",
    "serialNumber",
    "email",
}

# Zusätzlich in den Cloud-Daten: Die Site enthält ihre ID unter "id", die Organisation sowie Name
# und Adresse des Besitzers.
CLOUD_TO_REDACT: set[str] = TO_REDACT | {"id", "organisation_id", "name"}

# Datenpunkte, deren Werte ein Gerät oder eine Person identifizieren.
SENSITIVE_STATE_KEYS: set[str] = {"SERIAL_NUMBER", "LAST_RFID_CARD", "MAC_ADDRESS", "IP_ADDRESS"}


def _redact_states(states: dict[str, Any]) -> dict[str, Any]:
    """Entfernt die Werte identifizierender Datenpunkte aus der Zustandsliste."""
    redacted: dict[str, Any] = {}
    for state_id, item in states.items():
        if isinstance(item, dict) and item.get("key") in SENSITIVE_STATE_KEYS:
            item = {**item, "value": REDACTED}
        redacted[state_id] = item
    return redacted


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: NeoomConfigEntry) -> dict[str, Any]:
    """Liefert die Diagnosedaten eines Konfigurationseintrags."""
    cloud = entry.runtime_data.cloud
    local = entry.runtime_data.local
    local_data = local.data or {}

    return {
        "entry": async_redact_data(
            {
                "title": entry.title,
                "version": entry.version,
                "data": dict(entry.data),
                "options": dict(entry.options),
            },
            TO_REDACT,
        ),
        "cloud": {
            "last_update_success": cloud.last_update_success,
            "data": async_redact_data(cloud.data or {}, CLOUD_TO_REDACT),
        },
        "local": {
            "last_update_success": local.last_update_success,
            "unreachable_things": sorted(local._unreachable_things),
            "config": async_redact_data(local.beaam_config or {}, TO_REDACT),
            "states": _redact_states(local_data.get("states", {})),
            "settings": local_data.get("settings", {}),
        },
    }
