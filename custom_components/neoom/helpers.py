"""Hilfsfunktionen für die neoom AI Integration."""

from typing import Any, Dict, Optional, Tuple

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN, KNOWN_SETTINGS, SettingSpec

# Ab HA 2026.8 verweist DeviceInfo über die Registry-ID (via_device_id) auf das übergeordnete
# Gerät. Die Kennung über via_device ist veraltet und wird mit HA 2027.8 entfernt.
SUPPORTS_VIA_DEVICE_ID = "via_device_id" in dr.DeviceInfo.__annotations__


def gateway_identifier(site_id: str) -> Tuple[str, str]:
    """Liefert die Geräte-Kennung des BEAAM Gateways einer Site.

    Pro Site (= Konfigurationseintrag) gibt es genau ein BEAAM Gateway.
    """
    return (DOMAIN, f"beaam_{site_id}")


def classify_setting(key: str, value: Any) -> Tuple[Optional[SettingSpec], bool]:
    """Ordnet eine Einstellung genau einer Plattform zu.

    Returns:
        (Spezifikation, bekannt). Bekannte Einstellungen kommen aus KNOWN_SETTINGS. Für
        unbekannte rät eine Heuristik anhand von Schlüssel und Wert (Uhrzeit, Schalter, Zahl);
        (None, False), wenn keine Plattform passt.
    """
    if key in KNOWN_SETTINGS:
        return KNOWN_SETTINGS[key], True

    if isinstance(value, str):
        if key.endswith("_TIME") and ":" in value:
            return SettingSpec("time"), False
        if value.lower() in ("true", "false"):
            return SettingSpec("switch"), False

    is_number = isinstance(value, (int, float)) and not isinstance(value, bool)
    if isinstance(value, str) and ":" not in value:
        try:
            float(value)
            is_number = "." in value or value.lstrip("-").isdigit()
        except ValueError:
            pass
    if "ENERGY" in key:
        # Energiewerte liefert die API in Wh
        return SettingSpec("number", unit="kWh", device_class="energy", max_value=1000, step=0.1, scale=1000), False
    if is_number or "POWER" in key:
        return SettingSpec("number"), False
    return None, False


def virtual_sg_ready_dp_id(thing_id: str) -> str:
    """Liefert die ID des virtuellen SG-Ready-Datenpunkts einer Wärmepumpe."""
    return f"{thing_id}_operating_mode_sg_ready"


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
