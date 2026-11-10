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
* **Beta Pre-Releases:** Used to pre-test new features and bug fixes (e.g., `1.0.5-beta.1`). They are published as GitHub pre-releases and are only offered if you turn on the **Pre-release** switch (see [Installing a beta version](#en-beta)).

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

Since Home Assistant **2026.11**, community integrations are installed via the built-in **Marketplace** (the successor of HACS). There is nothing extra to install.

[![Open in the Home Assistant Marketplace](https://my.home-assistant.io/badges/marketplace_repository.svg)](https://my.home-assistant.io/redirect/marketplace_repository/?owner=MovingLlama&repository=neoom&category=integration)

#### A. Installing via the Marketplace (Home Assistant 2026.11 or newer)
1. Click the button above, or go to **Settings -> Marketplace** (administrators only).
   * If **neoom AI** is not listed yet: select **Add from link** in the upper-right corner, enter `MovingLlama/neoom` (or `https://github.com/MovingLlama/neoom`) under **GitHub link** and select **Add**. If asked for a type, choose **Integration**. Adding from a link requires a GitHub connection (sign-in via device code, read-only access to public data).
2. On first use, confirm the Marketplace warning (**I understand the risks**). Browsing works without it, installing does not.
3. Open **neoom AI**, select **Install**, check the version and select **Install** again.
4. The integration is loaded right away and the setup dialog opens – **no restart is needed** for the first installation. Continue with [Configuration](#en-config).

<a name="en-beta"></a>
#### B. Installing a beta version
1. Go to **Settings -> Devices & services -> Marketplace** and open the entities of the **neoom AI** repository.
2. The **Pre-release** switch is disabled by default: enable the entity first, then turn the switch on.
3. Pre-releases (e.g. `1.0.5-beta.1`) are now offered as updates as long as they are newer than the latest stable release. Turn the switch off to return to stable releases with the next stable version.
4. A specific version can also be installed via the three-dot menu of the repository page in the Marketplace -> **Install another version**.

#### C. Updates
* Available updates appear under **Settings -> Updates**, like the updates of Home Assistant itself (update entity of the Marketplace).
* ⚠️ **After an update, restart Home Assistant** (`Settings` -> `System` -> `Restart`). A repair under **Settings -> System -> Repairs** reminds you and can restart for you.

#### D. Coming from HACS?
Nothing to do: on the first start of Home Assistant 2026.11, the Marketplace takes over installations, custom repositories and update entities from HACS automatically. neoom AI stays installed, keeps its entities and continues to receive updates.

#### E. Home Assistant before 2026.11 (HACS)
On older versions, install via [HACS](https://hacs.xyz/): **HACS -> ⋮ -> Custom repositories**, add `https://github.com/MovingLlama/neoom` with category **Integration**, download **neoom AI** and restart Home Assistant. Beta versions: **⋮ -> Redownload -> Show beta versions**. The integration requires Home Assistant 2024.12 or newer.

#### F. Manual installation
Download `neoom.zip` from the [latest release](https://github.com/MovingLlama/neoom/releases/latest), extract it to `config/custom_components/neoom/` and restart Home Assistant. Manual installations do not get update notifications.

---

<a name="en-config"></a>
### ⚙️ Configuration

[![Add integration](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=neoom)

When installing via the Marketplace, the setup dialog opens automatically. Otherwise:
1. Go to **Settings -> Devices & Services** in Home Assistant.
2. Click **Add Integration** in the bottom right.
3. Search for **neoom AI** in the list.
4. Enter the neoom AI token, select your site from the list, enter the BEAAM IP address and API key, and save.

After successful setup, your devices and entities will appear automatically. New devices added to your neoom system are picked up within about 5 minutes, without a restart.

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
* This happens if Home Assistant hasn't loaded the integration files yet (e.g. after a manual or HACS installation, or after an update without a restart).
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
* **Beta Pre-Releases:** Vorabversionen zum Testen neuer Funktionen und Bugfixes (z. B. `1.0.5-beta.1`). Sie erscheinen auf GitHub als Pre-Release und werden nur angeboten, wenn der Schalter **Pre-release** aktiviert ist (siehe [Beta-Version installieren](#de-beta)).

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

Seit Home Assistant **2026.11** werden Community-Integrationen über den eingebauten **Marketplace** installiert (der Nachfolger von HACS). Es muss nichts zusätzlich installiert werden.

[![Open in the Home Assistant Marketplace](https://my.home-assistant.io/badges/marketplace_repository.svg)](https://my.home-assistant.io/redirect/marketplace_repository/?owner=MovingLlama&repository=neoom&category=integration)

#### A. Installation über den Marketplace (Home Assistant 2026.11 oder neuer)
1. Klicken Sie auf den Button oben oder gehen Sie zu **Einstellungen -> Marketplace** (nur für Administratoren).
   * Falls **neoom AI** dort noch nicht gelistet ist: Wählen Sie oben rechts **Add from link** (Über Link hinzufügen), geben Sie unter **GitHub link** `MovingLlama/neoom` (oder `https://github.com/MovingLlama/neoom`) ein und wählen Sie **Add** (Hinzufügen). Falls nach dem Typ gefragt wird, wählen Sie **Integration**. Für das Hinzufügen über einen Link ist eine Verbindung mit GitHub nötig (Anmeldung per Gerätecode, nur Lesezugriff auf öffentliche Daten).
2. Bestätigen Sie beim ersten Aufruf den Warnhinweis des Marketplace (**I understand the risks** / Ich verstehe die Risiken). Stöbern geht auch ohne, Installieren nicht.
3. Öffnen Sie **neoom AI**, wählen Sie **Install** (Installieren), prüfen Sie die Version und wählen Sie erneut **Install**.
4. Die Integration wird sofort geladen und der Einrichtungsdialog öffnet sich – **für die Erstinstallation ist kein Neustart nötig**. Weiter geht es mit der [Konfiguration](#de-config).

<a name="de-beta"></a>
#### B. Beta-Version installieren
1. Gehen Sie zu **Einstellungen -> Geräte & Dienste -> Marketplace** und öffnen Sie die Entitäten des Repositorys **neoom AI**.
2. Der Schalter **Pre-release** ist standardmäßig deaktiviert: Aktivieren Sie zuerst die Entität und schalten Sie den Schalter dann ein.
3. Ab jetzt werden Vorabversionen (z. B. `1.0.5-beta.1`) als Update angeboten, solange sie neuer sind als das letzte stabile Release. Schalten Sie den Schalter wieder aus, um mit der nächsten stabilen Version zu den stabilen Releases zurückzukehren.
4. Eine bestimmte Version lässt sich auch über das Drei-Punkte-Menü der Repository-Seite im Marketplace -> **Install another version** (Andere Version installieren) installieren.

#### C. Updates
* Verfügbare Updates erscheinen unter **Einstellungen -> Updates**, genau wie die Updates von Home Assistant selbst (Update-Entität des Marketplace).
* ⚠️ **Nach einem Update Home Assistant neu starten** (`Einstellungen` -> `System` -> `Neu starten`). Eine Reparaturmeldung unter **Einstellungen -> System -> Reparaturen** erinnert daran und kann den Neustart auslösen.

#### D. Umstieg von HACS
Nichts zu tun: Beim ersten Start von Home Assistant 2026.11 übernimmt der Marketplace Installationen, benutzerdefinierte Repositories und Update-Entitäten automatisch aus HACS. neoom AI bleibt installiert, behält seine Entitäten und bekommt weiterhin Updates.

#### E. Home Assistant vor 2026.11 (HACS)
Bei älteren Versionen erfolgt die Installation über [HACS](https://hacs.xyz/): **HACS -> ⋮ -> Benutzerdefinierte Repositories**, `https://github.com/MovingLlama/neoom` mit Kategorie **Integration** hinzufügen, **neoom AI** herunterladen und Home Assistant neu starten. Beta-Versionen: **⋮ -> Erneut herunterladen -> Beta-Versionen anzeigen**. Die Integration benötigt Home Assistant 2024.12 oder neuer.

#### F. Manuelle Installation
Laden Sie `neoom.zip` aus dem [neuesten Release](https://github.com/MovingLlama/neoom/releases/latest) herunter, entpacken Sie es nach `config/custom_components/neoom/` und starten Sie Home Assistant neu. Manuelle Installationen erhalten keine Update-Hinweise.

---

<a name="de-config"></a>
### ⚙️ Konfiguration

[![Add integration](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=neoom)

Bei der Installation über den Marketplace öffnet sich der Einrichtungsdialog automatisch. Ansonsten:
1. Gehen Sie in Home Assistant zu **Einstellungen -> Geräte & Dienste**.
2. Klicken Sie unten rechts auf **Integration hinzufügen**.
3. Suchen Sie in der Liste nach **neoom AI**.
4. Geben Sie das neoom AI Token ein, wählen Sie Ihren Standort aus der Liste, tragen Sie IP-Adresse und API Key des BEAAM ein und speichern Sie.

Nach erfolgreicher Einrichtung tauchen Ihre Geräte und Entitäten automatisch auf. Neue Geräte in Ihrem neoom-System werden innerhalb von etwa 5 Minuten ohne Neustart erkannt.

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
Dies passiert, wenn Home Assistant die Integrationsdateien noch nicht geladen hat (z. B. nach einer manuellen oder HACS-Installation oder nach einem Update ohne Neustart).
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
