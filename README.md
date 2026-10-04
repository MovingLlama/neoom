# neoom AI for Home Assistant

<img src="icon.png" width="60" height="60" align="center" alt="neoom Logo">

[English](#english) | [Deutsch](#deutsch)

---

<a name="english"></a>
## English

**neoom AI** is an unofficial custom integration for [Home Assistant](https://www.home-assistant.io/) that establishes a hybrid connection to your neoom systems (such as Staak, Beaam, etc.).

It connects the best of two worlds:
1. **neoom AI Cloud:** For tariff data.
2. **Local BEAAM Gateway:** For real-time data (updated every 15 seconds) without noticeable cloud latency.

---

### 🚀 Features (Stable Version)

All features listed below are fully included in the stable main version (branch `main`):

* **Real-time Monitoring:** Reads power, energy, and voltage data fast and directly from the local BEAAM Gateway in your network.
* **Smart Naming:** Automatically detects the "Friendly Names" (e.g., "PV South", "Heat Pump") of your devices from the neoom configuration, ensuring they are perfectly named in Home Assistant.
* **Dynamic Hardware Detection:** Automatically discovers inverters, batteries, charging stations, heat pumps, and meters without manual configuration.
* **Local Control:** Support for setting charging limits or operating modes (e.g. 1-phase/3-phase charging) directly via Home Assistant entities (sliders and dropdowns).
* **Ingest Data (Generic Devices):** Have meters that do not come from neoom? With the `neoom.ingest_state` service, you can send meter or sensor data from Home Assistant directly to the BEAAM Gateway (for devices configured as "Generic").
* **Tariff Information:** Integrates current electricity prices and feed-in tariffs from the neoom AI Cloud.
* **Easy Setup:** Convenient location (Site) selection via a dropdown menu during initial setup.
* **Fully Integrated:** All sensors are pre-configured with the correct Home Assistant device classes and state classes so they work seamlessly with the native Energy Dashboard.

---

### 🧪 Releases & Beta Testing

* **Stable Releases:** Tagged releases following semantic versioning (e.g., `1.0.0`, `1.0.4`).
* **Beta Pre-Releases:** Used to pre-test new features and bug fixes (e.g., `1.0.5-beta.1`). In HACS, enable **Show beta versions** on the integration to install pre-releases.

---

### 💡 Smart Charging & Operating Modes (Settings)

Various charging strategies and settings for your devices (such as battery and charging station) can be managed via the local BEAAM gateway:

* **EMS Operating Mode (`OPERATING_MODE_EMS`):**
  * **Intelligent (`GRIID_CONTROLLED`):** Uses the **neoom CONNECT Ai** optimization. Incorporates dynamic electricity tariffs (e.g. hourly variable prices), weather forecasts, and home consumption to shift charging to the cheapest, grid-friendly hours.
  * **Solar (`EXCESS_CONSUMPTION`):** Charges the battery, heat pump, or electric vehicle purely based on solar excess from your own PV system to maximize self-consumption.
  * **Excluded (`DEVICE_CONTROLLED`):** Excludes the device (e.g. Heat Pump or EV Charger) from EMS optimization.
* **SG-Ready Mode (`OPERATING_MODE_SG_READY`):** Shows the Smart Grid state of heat pumps (Mode 1: Forced OFF, Mode 2: Normal, Mode 3: Recommended ON, Mode 4: Forced ON). Usually the BEAAM Gateway sets this mode itself depending on available energy. A select entity to change it is only created if the gateway reports the data point as controllable; otherwise the mode is a read-only sensor.
* **Charge Quantity (`GRIID_CHARGING_ENERGY`):** Defines how much energy (in kWh) should be charged in intelligent mode.
* **Departure Time (`GRIID_EV_DEPARTURE_TIME`):** Sets the target time by which the charging process must be completed (provided as a native Time entity in Home Assistant).
* **Priority (`PRIORITY`):** Order in which devices in **Solar** mode receive the solar surplus (1 = first). The gateway only reports a value while the device is in Solar mode; in Intelligent mode the entity shows *unknown*, which is expected.

Further information and help setting up dynamic tariffs can be found in the [neoom GRIID article in the neoom knowledge base](https://wissen.neoom.com).

---

### 📋 Prerequisites

Before you start, you will need the following three pieces of information from your neoom/neoom AI account or hardware:

1. **neoom AI Bearer Token:** Your API access token for the neoom AI Cloud. (The site ID is queried automatically and can be selected from a list during setup).
2. **BEAAM IP Address:** The local IP address of your BEAAM Gateway in your home network (e.g., `192.168.1.50`).
3. **BEAAM API Key:** The local password / Local API key for accessing the gateway.

---

### 🛠 Installation

The easiest way to install is via [HACS](https://hacs.xyz/) (Home Assistant Community Store).

#### A. Installing the Stable Version
1. Open **HACS** in Home Assistant.
2. Go to **Integrations**.
3. Click the three dots `...` in the top right and select **Custom repositories**.
4. Add this repository URL: `https://github.com/MovingLlama/neoom`
5. Select category **Integration**.
6. Click "Add" and then download/install the integration from the list.
7. ⚠️ **IMPORTANT:** Restart Home Assistant completely (`Settings` -> `System` -> `Restart`) for the changes to take effect.

#### B. Installing the Beta Version
If you want to participate in beta tests:
1. Open **HACS** -> **Integrations**.
2. Find the already installed **neoom AI** integration (or add it as a Custom Repository as described above).
3. Click the three dots `...` and select **Redownload**.
4. Check the **Show beta versions** box.
5. Select the desired beta version (e.g., `1.0.1-beta-1`) from the list and click **Download**.
6. Restart Home Assistant completely.

---

### ⚙️ Configuration
1. Go to **Settings -> Devices & Services** in Home Assistant.
2. Click **Add Integration** in the bottom right.
3. Search for **neoom AI** in the list.
4. Enter the required credentials (Token, Site ID, IP, and Key) and save.

After successful setup, your devices and entities will appear automatically. New devices added to your neoom system are picked up within an hour, without a restart.

**Multiple sites:** Each site (with its BEAAM Gateway) is set up as its own integration entry. Simply add the integration again and select the next site; sites that are already set up are not offered again.

Access data (token, IP, key) can be changed later via the gear icon, **Reconfigure**, or the re-authentication prompt.

**Security note:** The BEAAM local API only offers unencrypted HTTP. The BEAAM API key and all values are sent in plain text on your network. Only use the integration within your trusted local network (ideally a separate VLAN for energy devices), and never forward the BEAAM's port to the internet. The neoom AI Cloud connection uses HTTPS.

---

### 📊 Supported Hardware & Sensors (Excerpt)

The integration automatically creates devices based on the hardware connected to your BEAAM Gateway:

| Device / Interface | Available Sensors & Controls |
| :--- | :--- |
| **neoom AI Cloud** | Electricity price (ct/kWh), feed-in tariff (ct/kWh) |
| **All devices** | Connection to the gateway (`CONNECTION`, binary sensor under "Diagnostic") |
| **BEAAM Gateway** | Net grid feed, total feed-in, grid frequency, voltages (L1/L2/L3), site-wide energy flow (e.g. house consumption, grid, storage, PV, total SoC – as reported by the gateway) |
| **Inverter** | Current power (W), energy produced (kWh), phase currents (A), power per input (`INPUTS_POWER`) |
| **PV** | Voltage and current per string (`VOLTAGES`/`CURRENTS`, one sensor per string), connection per string |
| **Battery Storage**| State of charge / SoC (%), charge/discharge power (W), temperature, state of health, backup power active (`EPS_MODE_ACTIVE`), error codes |
| **EV Charger** | Status (connected/charging), charging power, modes (1P/3P switching via select entity) |
| **Heat Pump** | Status, flow/return temperatures, thermal power, COP, SG-Ready mode (Modes 1-4; selectable only if the gateway reports it as controllable) & EMS mode (Solar / Excluded) |

> **Note on scaling:**
> Home Assistant displays native units by default (e.g., Watt or Watt-hours). You can change the display unit directly in the Home Assistant frontend (e.g., to Kilowatt `kW`) by clicking the cogwheel icon of the entity.

> **Note on the energy dashboard:**
> State of charge sensors (`SOC` / `STATE_OF_CHARGE`) use the device class *battery* and can be selected as the battery's state of charge.
> The "Untracked consumption" flow is calculated by Home Assistant itself (total home consumption minus the individual devices you added) – it is not a value of this integration. The site-wide house consumption reported by the gateway is available as an energy flow sensor on the BEAAM Gateway device.

---

### 🐛 Troubleshooting

**Error: "Invalid handler specified" when adding**
* This happens if Home Assistant hasn't loaded the integration files into cache yet.
* Solution: Restart Home Assistant and clear your browser cache.

**No real-time local data arriving (or entities unavailable)**
* Cloud connection usually works instantly, but local API issues occur if:
  1. The BEAAM Gateway IP address is incorrect or changed (Tip: Assign a static IP in your router).
  2. The BEAAM API Key is incorrect.
  3. The hardware is temporarily overloaded.

**Enable debug logging**
* To find out why the integration is failing, add this block to your `configuration.yaml` and restart Home Assistant:
```yaml
logger:
  default: info
  logs:
    custom_components.neoom: debug
```
* Search in *Settings -> System -> Logs* for entries starting with `neoom`.

**Diagnostics for bug reports**
* *Settings -> Devices & services -> neoom AI -> ⋮ -> Download diagnostics* creates a file with the device structure, current values and settings. Tokens, API key, IP address, site ID, site name/address, serial numbers and RFID cards are removed, so the file can be attached to an issue.

---

**Disclaimer:**
*This is an open-source community project and **not** official software by neoom ag. Use at your own risk.*

---
---

<a name="deutsch"></a>
## Deutsch

**neoom AI** ist eine inoffizielle "Custom Integration" für [Home Assistant](https://www.home-assistant.io/), die eine hybride Verbindung zu Ihren neoom-Systemen (wie Staak, Beaam, etc.) herstellt.

Sie verbindet das Beste aus zwei Welten:
1. **neoom AI Cloud:** Für Tarifdaten.
2. **Lokales BEAAM Gateway:** Für Echtzeit-Daten (Aktualisierung alle 15 Sekunden) ohne spürbare Cloud-Verzögerung.

---

### 🚀 Feature-Liste (Stabile Version)

Alle hier aufgelisteten Funktionen sind vollständig in der stabilen Hauptversion (Branch `main`) enthalten:

* **Echtzeit-Überwachung:** Liest Leistungs-, Energie- und Spannungsdaten blitzschnell direkt vom lokalen BEAAM Gateway im Netzwerk.
* **Intelligente Namensgebung:** Erkennt automatisch die "Friendly Names" (z. B. "PV Süd", "Wärmepumpe") deiner Geräte aus der neoom Konfiguration, sodass sie in Home Assistant perfekt benannt sind.
* **Dynamische Hardware-Erkennung:** Findet automatisch Wechselrichter, Batteriespeicher, Ladestationen, Wärmepumpen und Zähler, ohne dass du diese manuell konfigurieren musst.
* **Lokale Steuerung:** Unterstützung zum Setzen von Ladeleistungsgrenzen oder Betriebsmodi (z. B. 1-Phasig/3-Phasig Laden) direkt über Home Assistant-Entitäten (Slider und Dropdowns).
* **Daten einspeisen (Generic Devices):** Du hast Zähler, die nicht von neoom stammen? Mit dem Dienst `neoom.ingest_state` kannst du Zählerdaten oder Sensorwerte aus Home Assistant direkt an das BEAAM Gateway schicken (für als "Generic" konfigurierte Geräte).
* **Tarif-Informationen:** Integriert aktuelle Strompreise und Einspeisevergütungen aus der neoom AI Cloud.
* **Einfache Einrichtung:** Bequeme Auswahl deines Standorts (Site) über ein Dropdown-Menü bei der Ersteinrichtung.
* **Voll integriert:** Alle Sensoren sind mit den korrekten Home Assistant "Device Classes" und "State Classes" vorkonfiguriert, sodass sie nahtlos im nativen Energie-Dashboard (Energy Dashboard) verwendet werden können.

---

### 🧪 Releases & Beta-Tests

* **Stabile Releases:** Offizielle Versionen nach Semantic Versioning (z. B. `1.0.0`, `1.0.4`).
* **Beta Pre-Releases:** Vorabversionen zum Testen neuer Funktionen und Bugfixes (z. B. `1.0.5-beta.1`). In HACS kann dafür einfach das Häkchen bei **Beta-Versionen anzeigen** aktiviert werden.

---

### 💡 Intelligentes Laden & Betriebsmodi (Settings)

Über das lokale BEAAM-Gateway können verschiedene Ladestrategien und Einstellungen für deine Geräte (wie Batterie und Ladestation) verwaltet werden:

* **Betriebsmodus EMS (`OPERATING_MODE_EMS`):**
  * **Intelligent (`GRIID_CONTROLLED`):** Dieser Modus nutzt die **neoom CONNECT Ai** Optimierung. Das System bezieht dynamische Stromtarife (z. B. stündlich variable Strompreise), Wetterprognosen sowie den Hausverbrauch ein, um den Ladevorgang kosten- und netzschonend in die günstigsten Stunden zu verschieben.
  * **Solar (`EXCESS_CONSUMPTION`):** Lädt die Batterie, Wärmepumpe oder das Elektrofahrzeug rein basierend auf dem solaren Überschuss der eigenen PV-Anlage, um den Eigenverbrauch zu maximieren.
  * **Ausgenommen (`DEVICE_CONTROLLED`):** Nimmt das Gerät (z.B. Wärmepumpe) aus der automatischen EMS-Steuerung heraus.
* **SG-Ready Modus (`OPERATING_MODE_SG_READY`):** Zeigt den Smart-Grid-Zustand von Wärmepumpen (Mode 1: Sperre, Mode 2: Normal, Mode 3: Empfehlung, Mode 4: Fest EIN). In der Regel stellt das BEAAM Gateway den Modus selbst je nach verfügbarer Energie ein. Eine Auswahlentität zum Umstellen gibt es nur, wenn das Gateway den Datenpunkt als steuerbar meldet; sonst ist der Modus ein reiner Sensor.
* **Lademenge (`GRIID_CHARGING_ENERGY`):** Legt fest, wie viel Energie (in kWh) im intelligenten Modus geladen werden soll.
* **Abfahrtszeit (`GRIID_EV_DEPARTURE_TIME`):** Bestimmt den Zielzeitpunkt, zu dem der Ladevorgang abgeschlossen sein muss (wird als native Time-Entität in Home Assistant bereitgestellt).
* **Priorität (`PRIORITY`):** Reihenfolge, in der Geräte im Modus **Solar** den PV-Überschuss bekommen (1 = zuerst). Das Gateway liefert den Wert nur, solange das Gerät im Solar-Modus ist; im Modus Intelligent zeigt die Entität *unbekannt* – das ist so gewollt.

Weiterführende Informationen und Hilfe zur Einrichtung dynamischer Tarife findest du im [neoom GRIID-Artikel in der neoom Wissensdatenbank](https://wissen.neoom.com).

---

### 📋 Voraussetzungen

Bevor Sie mit der Installation starten, benötigen Sie folgende drei Informationen aus Ihrem neoom/neoom AI-Konto bzw. von Ihrer Hardware:

1. **neoom AI Bearer Token:** Ihr API-Zugriffsschlüssel für die neoom AI Cloud. (Der Standort bzw. die Site ID wird automatisch über dieses Token abgefragt und kann im nächsten Schritt bequem aus einer Liste ausgewählt werden).
2. **BEAAM IP-Adresse:** Die lokale IP-Adresse Ihres BEAAM Gateways in Ihrem Heimnetzwerk (z. B. `192.168.1.50`).
3. **BEAAM API Key:** Das lokale Passwort bzw. der Local-API-Key für den Zugriff auf das Gateway.

---

### 🛠 Installation

Die einfachste Methode zur Installation ist über [HACS](https://hacs.xyz/) (Home Assistant Community Store).

#### A. Stabile Version installieren
1. Öffnen Sie **HACS** in Ihrem Home Assistant.
2. Gehen Sie zum Reiter **Integrations**.
3. Klicke oben rechts auf die drei Punkte `...` und wählen Sie **Custom repositories** (Benutzerdefinierte Repositories).
4. Fügen Sie die URL dieses Repositories hinzu: `https://github.com/MovingLlama/neoom`
5. Wählen Sie als Kategorie **Integration**.
6. Klicken Sie auf "Hinzufügen" und anschließend in der Liste auf "Herunterladen" bzw. "Installieren".
7. ⚠️ **WICHTIG:** Starten Sie Home Assistant komplett neu (`Einstellungen` -> `System` -> `Neu starten`), damit Home Assistant den neuen Code laden kann.

#### B. Beta-Version installieren
Falls Sie an Beta-Tests teilnehmen möchten:
1. Öffnen Sie **HACS** -> **Integrations**.
2. Suchen Sie nach der bereits installierten **neoom AI** Integration (oder fügen Sie sie wie oben beschrieben als Custom Repository hinzu).
3. Klicken Sie auf die drei Punkte `...` der Integration und wählen Sie **Redownload** (Erneut herunterladen).
4. Aktivieren Sie das Kontrollkästchen **Show beta versions** (Beta-Versionen anzeigen).
5. Wählen Sie die gewünschte Beta-Version (z. B. `1.0.1-beta-1`) aus der Liste aus und klicken Sie auf **Herunterladen**.
6. Starten Sie Home Assistant komplett neu.

---

### ⚙️ Konfiguration

1. Gehen Sie nach dem Neustart in Home Assistant zu **Einstellungen -> Geräte & Dienste**.
2. Klicken Sie unten rechts auf **Integration hinzufügen**.
3. Suchen Sie in der Liste nach **neoom AI**.
4. Geben Sie die erforderlichen Daten (Token, Site ID, IP und Key) in das Formular ein und speichern Sie.

Nach erfolgreicher Einrichtung tauchen Ihre Geräte und Entitäten automatisch auf. Neue Geräte in Ihrem neoom-System werden innerhalb einer Stunde ohne Neustart erkannt.

**Mehrere Standorte:** Jeder Standort (Site) mit seinem BEAAM Gateway wird als eigener Integrationseintrag eingerichtet. Fügen Sie die Integration einfach erneut hinzu und wählen Sie den nächsten Standort; bereits eingerichtete Standorte werden nicht mehr angeboten.

Zugangsdaten (Token, IP, Key) können später über das Zahnrad, **Neu konfigurieren** oder die Aufforderung zur erneuten Anmeldung geändert werden.

**Sicherheitshinweis:** Die lokale API des BEAAM bietet nur unverschlüsseltes HTTP an. Der BEAAM API Key und alle Werte gehen im Klartext durch Ihr Netzwerk. Verwenden Sie die Integration nur in Ihrem vertrauenswürdigen lokalen Netz (idealerweise einem eigenen VLAN für Energiegeräte) und geben Sie den Port des BEAAM niemals ins Internet frei. Die Verbindung zur neoom AI Cloud nutzt HTTPS.

---

### 📊 Unterstützte Hardware & Sensoren (Auszug)

Die Integration erstellt automatisch Geräte (Devices) basierend auf der an Ihr BEAAM Gateway angebundenen Hardware:

| Gerät / Schnittstelle | Verfügbare Sensoren & Steuerungen |
| :--- | :--- |
| **neoom AI Cloud** | Strompreis (ct/kWh), Einspeisetarif (ct/kWh) |
| **Alle Geräte** | Verbindung zum Gateway (`CONNECTION`, Binärsensor unter „Diagnose“) |
| **BEAAM Gateway** | Gesamt-Netzbezug, Gesamte Einspeisung, Netzfrequenz, Spannungen (L1/L2/L3), standortweiter Energiefluss (z. B. Hausverbrauch, Netz, Speicher, PV, Gesamt-SoC – je nachdem, was das Gateway meldet) |
| **Wechselrichter** | Aktuelle Leistung (W), Produzierte Energie (kWh), Phasen-Ströme (A), Leistung pro Eingang (`INPUTS_POWER`) |
| **PV** | Spannung und Strom pro String (`VOLTAGES`/`CURRENTS`, ein Sensor pro String), Verbindung pro String |
| **Batteriespeicher**| Ladezustand / SoC (%), Lade-/Entladeleistung (W), Temperatur, State of Health, Notstrom aktiv (`EPS_MODE_ACTIVE`), Fehlercodes |
| **E-Ladestation** | Status (Verbunden/Lädt), Ladeleistung, Modi (1P/3P Umschaltung über Select-Entität) |
| **Wärmepumpe** | Status, Vorlauf-/Rücklauftemperaturen, Wärmeleistung, COP, SG-Ready Modus (Mode 1-4; umstellbar nur, wenn das Gateway ihn als steuerbar meldet) & EMS-Betriebsmodus (Solar / Ausgenommen) |

> **Hinweis zur Skalierung:**
> Home Assistant zeigt Ihnen standardmäßig die nativen Einheiten an (z. B. Watt oder Wattstunden). Sie können die Anzeigeeinheit direkt in der Benutzeroberfläche von Home Assistant umstellen (z. B. auf Kilowatt `kW`), indem Sie auf das Zahnrad-Symbol der jeweiligen Entität klicken.

> **Hinweis zum Energie-Dashboard:**
> Ladezustands-Sensoren (`SOC` / `STATE_OF_CHARGE`) haben die Geräteklasse *Batterie* und können als Ladezustand des Speichers ausgewählt werden.
> Der Fluss „Nicht erfasster Verbrauch“ wird von Home Assistant selbst berechnet (Gesamt-Hausverbrauch abzüglich der einzeln hinzugefügten Geräte) und ist kein Wert dieser Integration. Den vom Gateway gemeldeten Hausverbrauch des Standorts finden Sie als Energiefluss-Sensor am Gerät „BEAAM Gateway“.

---

### 🐛 Fehlerbehebung (Troubleshooting)

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

**Diagnosedaten für Fehlerberichte**
Unter *Einstellungen -> Geräte & Dienste -> neoom AI -> ⋮ -> Diagnosedaten herunterladen* erstellt Home Assistant eine Datei mit Gerätestruktur, aktuellen Werten und Einstellungen. Token, API-Key, IP-Adresse, Site-ID, Name/Adresse der Site, Seriennummern und RFID-Karten sind entfernt, sodass die Datei einem Issue angehängt werden kann.

---

**Disclaimer:** 
*Dies ist ein Open-Source-Community-Projekt und **keine** offizielle Software der neoom ag. Nutzung auf eigene Gefahr.*
