"""Hilfsfunktionen für die neoom AI Integration."""

from typing import Any, Dict

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN


def get_friendly_thing_name(beaam_config: Dict[str, Any], thing_id: str, default_type: str) -> str:
    """Extrahiert einen benutzerfreundlichen Namen für ein Gerät (Thing) aus der BEAAM Konfiguration.
    
    Durchsucht zuerst das Thing-Objekt selbst und anschließend die siteInfo.
    Gibt als Fallback den bereinigten Gerätetyp zurück.
    """
    if not beaam_config:
        return default_type.replace("_", " ").title()

    # 1. Prüfen, ob das Thing selbst einen Namen hat
    things = beaam_config.get("things", {})
    thing = things.get(thing_id, {})
    if isinstance(thing, dict) and thing.get("name"):
        return str(thing["name"])

    # 2. siteInfo durchsuchen (z.B. gridConnections, inverters, storages, pvPlants)
    site_info = beaam_config.get("siteInfo", {})
    if isinstance(site_info, dict):
        for category, items in site_info.items():
            if isinstance(items, dict):
                for item_id, item_data in items.items():
                    if isinstance(item_data, dict):
                        # Ist die ID der Eintragung identisch mit unserer thing_id?
                        # Oder steht die thing_id als Wert in einem der Felder (z.B. meterThingId)?
                        if item_id == thing_id or thing_id in item_data.values():
                            if item_data.get("name"):
                                return str(item_data["name"])

    # 3. Fallback auf den (lesbar gemachten) technischen Typen
    return default_type.replace("_", " ").title()


def is_generic_thing(thing_data: Dict[str, Any]) -> bool:
    """Prüft, ob ein Gerät (Thing) ein Generic Device ist.

    Nur Generic Devices nehmen Werte per State-Ingest an. Ihr Typ enthält
    "generic" (Groß-/Kleinschreibung wird ignoriert).
    """
    return "GENERIC" in str(thing_data.get("type") or "").upper()


def is_ingest_entity_wanted(
    hass: HomeAssistant, platform: str, unique_id: str, thing_data: Dict[str, Any]
) -> bool:
    """Entscheidet, ob für einen Datenpunkt eine Ingest-Entität angelegt wird.

    Angelegt wird sie für Generic Devices sowie für bestehende Ingest-Entitäten,
    die der Benutzer selbst aktiviert hat (damit keine Automationen brechen).
    """
    if is_generic_thing(thing_data):
        return True

    registry = er.async_get(hass)
    entity_id = registry.async_get_entity_id(platform, DOMAIN, unique_id)
    if entity_id is None:
        return False
    entry = registry.async_get(entity_id)
    return entry is not None and entry.disabled_by is None
