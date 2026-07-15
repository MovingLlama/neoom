# neoom AI für Home Assistant

<img src="https://neoom.com/hubfs/01_neoom%20Website%20neu/Icons/Icon_Systemicons/neoom_round_c.svg" width="60" height="60" align="center" alt="neoom Logo">

**neoom AI** ist eine inoffizielle "Custom Integration" für [Home Assistant](https://www.home-assistant.io/), die eine hybride Verbindung zu Ihren neoom-Systemen (wie Kjuube, Beaam, etc.) herstellt. 

Sie verbindet das Beste aus zwei Welten:
1. **neoom AI Cloud:** Für Tarifdaten, Wettervorhersagen und statistische Werte.
2. **Lokales BEAAM Gateway:** Für Echtzeit-Daten (im Sekundentakt) ohne spürbare Cloud-Verzögerung.

---

## 🚀 Funktionen

* **Echtzeit-Überwachung:** Liest Leistungs-, Energie- und Spannungsdaten blitzschnell direkt vom lokalen BEAAM Gateway im Netzwerk.
* **Intelligente Namensgebung:** Erkennt automatisch die "Friendly Names" (z. B. "PV Süd", "Wärmepumpe") deiner Geräte aus der neoom Konfiguration, sodass sie in Home Assistant perfekt benannt sind.
* **Dynamische Hardware-Erkennung:** Findet automatisch Wechselrichter, Batterien (z. B. Kjuube), Ladestationen und Zähler, ohne dass du diese manuell konfigurieren musst.
* **Steuerung (Beta):** Unterstützung zum Setzen von Ladeleistungsgrenzen oder Betriebsmodi (z. B. 1-Phasig/3-Phasig Laden) direkt über Home Assistant-Entitäten (Slider und Dropdowns).
* **Daten einspeisen (Generic Devices):** Du hast Zähler, die nicht von neoom stammen? Mit dem Dienst `neoom.ingest_state` kannst du Zählerdaten oder Sensorwerte aus Home Assistant direkt an das BEAAM Gateway schicken (für als "Generic" konfigurierte Geräte).
* **Tarif-Informationen:** Integriert aktuelle Strompreise und Einspeisevergütungen aus der neoom AI Cloud.
* **Einfache Einrichtung:** Bequeme Auswahl deines Standorts (Site) über ein Dropdown-Menü bei der Ersteinrichtung.
* **Voll integriert:** Alle Sensoren sind mit den korrekten Home Assistant "Device Classes" und "State Classes" vorkonfiguriert, sodass sie nahtlos im nativen Energie-Dashboard (Energy Dashboard) verwendet werden können.

## 💡 Intelligentes Laden & Betriebsmodi (Settings)

Über das lokale BEAAM-Gateway können verschiedene Ladestrategien und Einstellungen für deine Geräte (wie Batterie und Ladestation) verwaltet werden:

*   **Betriebsmodus EMS (`OPERATING_MODE_EMS`):**
    *   **Intelligent (`GRIID_CONTROLLED`):** Dieser Modus nutzt die **neoom CONNECT Ai** Optimierung. Das System bezieht dynamische Stromtarife (z. B. stündlich variable Strompreise), Wetterprognosen sowie den Hausverbrauch ein, um den Ladevorgang kosten- und netzschonend in die günstigsten Stunden zu verschieben.
    *   **Solar (`DEVICE_CONTROLLED`):** Lädt die Batterie oder das Elektrofahrzeug rein basierend auf dem solaren Überschuss der eigenen PV-Anlage, um den Eigenverbrauch zu maximieren.
*   **Lademenge (`GRIID_CHARGING_ENERGY`):** Legt fest, wie viel Energie (in kWh) im intelligenten Modus geladen werden soll.
*   **Abfahrtszeit (`GRIID_EV_DEPARTURE_TIME`):** Bestimmt den Zielzeitpunkt, zu dem der Ladevorgang abgeschlossen sein muss (wird als native Time-Entität in Home Assistant bereitgestellt).

Weiterführende Informationen und Hilfe zur Einrichtung dynamischer Tarife findest du im [neoom GRIID-Artikel in der neoom Wissensdatenbank](https://wissen.neoom.com).

## 📋 Voraussetzungen

Bevor Sie mit der Installation starten, benötigen Sie folgende drei Informationen aus Ihrem neoom/neoom AI-Konto bzw. von Ihrer Hardware:

1. **neoom AI Bearer Token:** Ihr API-Zugriffsschlüssel für die neoom AI Cloud. (Der Standort bzw. die Site ID wird automatisch über dieses Token abgefragt und kann im nächsten Schritt bequem aus einer Liste ausgewählt werden).
2. **BEAAM IP-Adresse:** Die lokale IP-Adresse Ihres BEAAM Gateways in Ihrem Heimnetzwerk (z. B. `192.168.1.50`).
3. **BEAAM API Key:** Das lokale Passwort bzw. der Local-API-Key für den Zugriff auf das Gateway.

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
4. Geben Sie die erforderlichen Daten (Token, Site ID, IP und Key) in das Formular ein und speichern Sie.

Nach erfolgreicher Einrichtung tauchen Ihre Geräte und Entitäten automatisch auf.

## 📊 Unterstützte Hardware & Sensoren (Auszug)

Die Integration erstellt automatisch Geräte (Devices) basierend auf der an Ihr BEAAM Gateway angebundenen Hardware:

| Gerät / Schnittstelle | Verfügbare Sensoren & Steuerungen |
| :--- | :--- |
| **neoom AI Cloud** | Strompreis (EUR/kWh), Einspeisetarif (ct/kWh) |
| **BEAAM Gateway (Lokal)** | Gesamt-Netzbezug, Gesamte Einspeisung, Netzfrequenz, Spannungen (L1/L2/L3) |
| **Wechselrichter (Inverter)** | Aktuelle Leistung (W), Produzierte Energie (kWh), Phasen-Ströme (A) |
| **Batteriespeicher (Kjuube)**| Ladezustand / SoC (%), Lade-/Entladeleistung (W), Temperatur, State of Health |
| **E-Ladestation** | Status (Verbunden/Lädt), Ladeleistung, Modi (1P/3P Umschaltung über Select-Entität) |

> **Hinweis zur Skalierung:**
> Home Assistant zeigt Ihnen standardmäßig die nativen Einheiten an (z. B. Watt oder Wattstunden). Sie können die Anzeigeeinheit direkt in der Benutzeroberfläche von Home Assistant umstellen (z. B. auf Kilowatt `kW`), indem Sie auf das Zahnrad-Symbol der jeweiligen Entität klicken.

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
