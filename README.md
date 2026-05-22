# neoom AI für Home Assistant

<img src="https://neoom.com/hubfs/01_neoom%20Website%20neu/Icons/Icon_Systemicons/neoom_round_c.svg" width="60" height="60" align="center" alt="neoom Logo">

**neoom AI** ist eine inoffizielle "Custom Integration" für [Home Assistant](https://www.home-assistant.io/), die eine hybride Verbindung zu Ihren neoom-Systemen (wie Kjuube, Beaam, etc.) herstellt. 

Sie verbindet das Beste aus zwei Welten:
1. **neoom AI Cloud:** Für Tarifdaten, Wettervorhersagen, Standort-Metadaten und den aggregierten Cloud-Energiefluss (als Fallback).
2. **Lokales BEAAM Gateway:** Für Echtzeit-Daten (im Sekundentakt) ohne spürbare Cloud-Verzögerung.

---

## 🚀 Funktionen

* **Automatische Standort-Erkennung (Site Discovery):** Sie müssen Ihre `Site ID` nicht mehr mühsam suchen oder kopieren. Die Integration ruft alle mit Ihrem neoom AI Token verknüpften Standorte automatisch ab. Gibt es mehrere Standorte, können Sie den gewünschten in einem Dropdown-Menü auswählen.
* **Echtzeit-Überwachung (Lokal):** Liest Leistungs-, Energie- und Spannungsdaten blitzschnell direkt vom lokalen BEAAM Gateway im Netzwerk.
* **Dynamische Hardware-Erkennung:** Findet automatisch Wechselrichter, Batterien (z. B. Kjuube), Ladestationen und Zähler, ohne dass Sie diese manuell konfigurieren müssen.
* **Cloud Energiefluss (10 Fallback-Sensoren):** Integration von Live-Werten direkt aus der neoom AI Cloud als Backup oder zur Ergänzung lokaler Messdaten (Produktion, Hausverbrauch, Batterie-SoC, Autarkiegrad etc.).
* **Standort-Metadaten:** Liefert wichtige Kennzahlen wie den aktuellen CO₂-Faktor (kg/kWh) und die maximale Netzwerkauslastung (W).
* **Zwei-Wege-Zustandsübertragung (State Ingestion):** Übertragen Sie Messdaten von Home Assistant-Fremdsensoren (z. B. Shelly, Zigbee-Zähler) direkt zurück an Ihr BEAAM Gateway, damit dieses die Daten lokal verarbeiten und regeln kann.
* **Steuerung (Beta):** Unterstützung zum Setzen von Ladeleistungsgrenzen oder Betriebsmodi (z. B. 1-Phasig/3-Phasig Laden) direkt über Home Assistant-Entitäten (Slider und Dropdowns).
* **Tarif-Informationen:** Integriert aktuelle Strompreise und Einspeisevergütungen aus der neoom AI Cloud.
* **Voll integriert:** Alle Sensoren sind mit den korrekten Home Assistant "Device Classes" und "State Classes" vorkonfiguriert, sodass sie nahtlos im nativen Energie-Dashboard (Energy Dashboard) verwendet werden können.

## 📋 Voraussetzungen

Bevor Sie mit der Installation starten, benötigen Sie folgende drei Informationen aus Ihrem neoom/neoom AI-Konto bzw. von Ihrer Hardware:

1. **neoom AI Bearer Token:** Ihr API-Zugriffsschlüssel für die neoom AI Cloud.
2. **BEAAM IP-Adresse:** Die lokale IP-Adresse Ihres BEAAM Gateways in Ihrem Heimnetzwerk (z. B. `192.168.1.50`).
3. **BEAAM API Key:** Das lokale Passwort bzw. der Local-API-Key für den Zugriff auf das Gateway.

*(Hinweis: Die **Site ID** wird ab sofort vollautomatisch ermittelt!)*

## 🛠 Installation

Die einfachste Methode zur Installation ist über [HACS](https://hacs.xyz/) (Home Assistant Community Store).

1. Öffnen Sie **HACS** in Ihrem Home Assistant.
2. Gehen Sie zum Reiter **Integrations**.
3. Klicke oben rechts auf die drei Punkte `...` und wählen Sie **Custom repositories** (Benutzerdefinierte Repositories).
4. Fügen Sie die URL dieses Repositories hinzu: `https://github.com/MovingLlama/neoom`
5. Wählen Sie als Kategorie **Integration**.
6. Klicken Sie auf "Hinzufügen" und anschließend in der Liste auf "Herunterladen" bzw. "Installieren".
7. ⚠️ **WICHTIG:** Starten Sie Home Assistant komplett neu (`Einstellungen` -> `System` -> `Neu starten`), damit Home Assistant den neuen Code laden kann.

## ⚙️ Konfiguration

1. Gehen Sie nach dem Neustart in Home Assistant zu **Einstellungen -> Geräte & Dienste**.
2. Klicken Sie unten rechts auf **Integration hinzufügen**.
3. Suchen Sie in der Liste nach **neoom AI**.
4. Geben Sie Ihr **neoom AI Bearer Token**, die **BEAAM IP-Adresse** und den **BEAAM API Key** ein.
5. Falls unter Ihrem Account mehrere Standorte (Sites) registriert sind, erscheint im nächsten Schritt ein Dropdown-Menü, in dem Sie den gewünschten Standort auswählen können. Bei nur einem Standort wird dieser automatisch ausgewählt.
6. Speichern Sie die Konfiguration.

## 📊 Unterstützte Hardware & Sensoren

Die Integration erstellt automatisch Geräte (Devices) basierend auf den Cloud-Daten und der an Ihr BEAAM Gateway angebundenen Hardware:

| Gerät / Schnittstelle | Verfügbare Sensoren & Steuerungen |
| :--- | :--- |
| **neoom AI Cloud** | Strompreis (EUR/kWh), Einspeisetarif (ct/kWh), CO₂-Faktor (kg/kWh), Max. Netzwerkauslastung (W) |
| **neoom AI Cloud (Energy Flow)** | Solar-Leistung (W), Hausverbrauch (W), Batterie-Lade/Entladeleistung (W), Batterie-Ladezustand (%), Netzleistung (W), Autarkiegrad (%), Eigenverbrauchsquote (%), Ladestationen-Leistung (W), CO₂-Ersparnis (kg), Heutiger Ertrag (EUR) |
| **BEAAM Gateway (Lokal)** | Gesamt-Netzbezug, Gesamte Einspeisung, Netzfrequenz, Spannungen (L1/L2/L3) |
| **Wechselrichter (Inverter)** | Aktuelle Leistung (W), Produzierte Energie (kWh), Phasen-Ströme (A) |
| **Batteriespeicher (Kjuube)**| Ladezustand / SoC (%), Lade-/Entladeleistung (W), Temperatur, State of Health |
| **E-Ladestation** | Status (Verbunden/Lädt), Ladeleistung, Modi (1P/3P Umschaltung über Select-Entität) |

## 🔌 Dienste (Services)

### Dienst `neoom.ingest_state`

Dieser Service ermöglicht die manuelle Übertragung (Ingestion) von Sensordaten von Home Assistant an das BEAAM Gateway. Dies ist besonders nützlich, wenn Sie Fremdgeräte (wie Shelly-Messer oder Wechselrichter anderer Marken) verwenden, deren Daten das BEAAM Gateway für lokale Optimierungen oder Visualisierungen benötigt.

**Service-Parameter:**
* **Geräte-ID (thing_id):** Die eindeutige UUID des zu aktualisierenden Geräts (z. B. des generischen Zählers) auf Ihrem BEAAM Gateway.
* **Zustandsschlüssel (key):** Der genaue Telemetrie-Key, der aktualisiert werden soll (z. B. `CURRENT_P1`, `ACTIVE_POWER_PLUS`, `VOLTAGE_L1`).
* **Wert (value):** Der neue Zustandswert (Zahl oder String), der übermittelt werden soll.

**Beispiel für einen Automatisierungs-Aufruf (YAML):**
```yaml
service: neoom.ingest_state
data:
  thing_id: "00000000-0000-0000-0000-000000000000"
  key: "ACTIVE_POWER_PLUS"
  value: 450.5
```

## 🐛 Fehlerbehebung (Troubleshooting)

**Fehler: "Invalid handler specified" beim Hinzufügen**
Dies passiert, wenn Home Assistant die neuen Integrationsdateien noch nicht in den Cache geladen hat.
* Lösung: Starten Sie Home Assistant neu (ggf. auch den Browser-Cache leeren).

**Keine lokalen Echtzeit-Daten kommen an (oder Entitäten sind nicht verfügbar)**
Die Verbindung zur neoom AI Cloud funktioniert meist auf Anhieb, lokale API-Probleme treten jedoch auf, wenn:
1. Die IP-Adresse des BEAAM Gateways falsch ist oder sich geändert hat (Tipp: Weisen Sie dem Gateway im Router eine statische IP zu).
2. Der verwendete BEAAM API Key inkorrekt ist.
3. Die Hardware temporär überlastet ist.

**Erweitertes Logging aktivieren**
Um herauszufinden, warum die Integration nicht funktioniert, fügen Sie folgenden Block in Ihre `configuration.yaml` ein und starten Sie Home Assistant neu:

```yaml
logger:
  default: info
  logs:
    custom_components.neoom: debug
```
Suchen Sie anschließend unter *Einstellungen -> System -> Protokolle* nach Einträgen mit dem Präfix `neoom`.

---

**Disclaimer:** 
*Dies ist ein Open-Source-Community-Projekt und **keine** offizielle Software der neoom ag. Nutzung auf eigene Gefahr.*
