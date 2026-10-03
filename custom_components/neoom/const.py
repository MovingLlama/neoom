"""Konstanten für die neoom AI Integration."""

from dataclasses import dataclass
from logging import Logger, getLogger
from typing import Optional

# Zentraler Logger für die gesamte Integration, erleichtert das Debugging.
LOGGER: Logger = getLogger(__package__)

# Der eindeutige Bezeichner (Domain) der Integration in Home Assistant.
DOMAIN: str = "neoom"

# Der Anzeigename der Integration in der Benutzeroberfläche.
NAME: str = "neoom AI"

# --- Konfigurations-Schlüssel ---
# Diese Schlüssel werden im Config Flow (`config_flow.py`) abgefragt
# und in den Eintragsdaten (`entry.data` in `__init__.py`) gespeichert.

# Die eindeutige ID des Standorts (Site) in der neoom AI Cloud.
CONF_SITE_ID: str = "site_id"

# Das Bearer-Token für die Authentifizierung an der neoom AI Cloud API.
CONF_CLOUD_TOKEN: str = "cloud_token"

# Die lokale IP-Adresse des BEAAM Gateways in Ihrem Netzwerk.
CONF_BEAAM_IP: str = "beaam_ip"

# Der API-Schlüssel (Token) für den lokalen Zugriff auf das BEAAM Gateway.
CONF_BEAAM_KEY: str = "beaam_key"


# --- API Endpunkte und Ports ---

# Die Basis-URL für die neoom AI Cloud API (Version 1).
CLOUD_API_URL: str = "https://api.ntuity.io/v1"

# Der Standard-Port für HTTP-Anfragen an das lokale BEAAM Gateway.
# Wird aktuell nicht explizit in den URLs verwendet (da 80 implizit ist),
# dient aber der Dokumentation.
LOCAL_API_PORT: int = 80


# --- Standard Aktualisierungsintervalle & Optionen ---

# Option-Schlüssel für die Aktualisierungsintervalle
CONF_SCAN_INTERVAL_CLOUD: str = "scan_interval_cloud"
CONF_SCAN_INTERVAL_LOCAL: str = "scan_interval_local"

# Das Intervall in Sekunden, in dem Daten aus der Cloud abgerufen werden.
# Da sich diese Daten (wie Preise oder Tarife) selten ändern, genügen 5 Minuten.
DEFAULT_SCAN_INTERVAL_CLOUD: int = 300  

# Das Intervall in Sekunden, in dem Live-Daten vom lokalen BEAAM Gateway
# abgerufen werden. Ein kurzer Intervall ist wichtig für Live-Energieflüsse.
DEFAULT_SCAN_INTERVAL_LOCAL: int = 15


# Intervall in Sekunden, nach dem die Gerätestruktur (site/configuration) neu geladen wird,
# damit neu angelegte Geräte im neoom-System ohne Neustart erkannt werden.
CONFIG_REFRESH_INTERVAL: int = 3600

# Wartezeit in Sekunden bis zum nächsten Versuch, wenn das Neuladen der Gerätestruktur fehlschlägt.
CONFIG_RETRY_INTERVAL: int = 300

# Wartezeit in Sekunden, bis nach einer Einstellungsänderung neu abgefragt wird. Das Gateway
# übernimmt Einstellungen mit kurzer Verzögerung.
SETTING_REFRESH_DELAY: float = 1.5

# Suffixe der Unique-IDs von Ingest-Entitäten (Number und Select).
INGEST_UID_SUFFIXES: tuple[str, ...] = ("_ingest", "_ingest_select")


# --- Einstellungen (Settings) der Things ---


@dataclass(frozen=True)
class SettingSpec:
    """Beschreibt, als welche Entität eine Einstellung des Gateways angelegt wird."""

    platform: str  # "number", "select", "switch" oder "time"
    name: Optional[str] = None
    unit: Optional[str] = None
    device_class: Optional[str] = None
    min_value: float = 0
    max_value: float = 1_000_000
    step: float = 1
    # Faktor zwischen API- und HA-Wert (HA-Wert = API-Wert / scale), z. B. 1000 für Wh -> kWh
    scale: float = 1


# Bekannte Einstellungen. Sie werden mit passender Plattform, Einheit und Wertebereich angelegt.
# Unbekannte Einstellungen erkennt eine Heuristik anhand von Schlüssel und Wert; solche
# Entitäten sind standardmäßig deaktiviert.
KNOWN_SETTINGS: dict[str, SettingSpec] = {
    "OPERATING_MODE_EMS": SettingSpec("select"),
    "BATTERY_CHARGE_FROM_GRID_ALLOWED": SettingSpec("switch", name="Allow battery charging from grid"),
    "BATTERY_DISCHARGE_TO_GRID_ALLOWED": SettingSpec("switch", name="Allow battery discharging to grid"),
    "GRIID_EV_DEPARTURE_TIME": SettingSpec("time", name="Departure time"),
    "GRIID_CHARGING_ENERGY": SettingSpec(
        "number", name="Lademenge", unit="kWh", device_class="energy", max_value=1000, step=0.1, scale=1000
    ),
    "PRIORITY": SettingSpec("number"),
    "POWER_THRESHOLD_NORMAL_OP": SettingSpec("number", unit="W", device_class="power"),
    "POWER_THRESHOLD_RECOMMENDED_OP": SettingSpec("number", unit="W", device_class="power"),
    "RAMP_UP_TIME": SettingSpec("number", unit="s", device_class="duration"),
    "LOCK_TIME": SettingSpec("number", unit="s", device_class="duration"),
}
