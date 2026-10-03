# Changelog

## 1.1.4

### Geändert
- **SG-Ready bei Wärmepumpen ohne eigenen Datenpunkt ist nur noch lesend.** Meldet das Gateway bei einer Wärmepumpe keinen SG-Ready-Datenpunkt, ergänzt die Integration ihn weiterhin, damit der Modus als Sensor angezeigt wird. Die Auswahl zum Umstellen entfällt jedoch: Das Gateway kennt diesen Datenpunkt nicht, Befehle dafür wurden nicht zuverlässig umgesetzt. Gesteuert wird nur, was das Gateway selbst als steuerbar meldet. Bestehende Auswahl-Entitäten dieses virtuellen Datenpunkts werden automatisch entfernt. Wärmepumpen, deren Gateway SG-Ready als steuerbar meldet, sind nicht betroffen.

### Behoben
- Einstellungen (Number, Select, Switch, Time) werden nicht mehr als fehlgeschlagen gemeldet, wenn das Gateway sie angenommen hat, der anschließende Abgleich aber länger dauert. Der Abgleich läuft jetzt 1,5 s später im Hintergrund, statt innerhalb des 10-s-Timeouts des Sendens. Die Bedienung in der Oberfläche blockiert dadurch nicht mehr. Mehrere Änderungen kurz hintereinander lösen nur einen Abgleich aus.
- Auch nach Befehlen und `neoom.ingest_state` zählt der Abgleich nicht mehr zum Timeout des Sendens.

### Verbessert
- Der Antworttext des Gateways nach einer Einstellungsänderung steht nur noch im Debug-Log statt bei jeder Änderung im normalen Log.
- Hinweis in README und Einrichtungsdialog: Die lokale BEAAM-API ist unverschlüsseltes HTTP (das BEAAM bietet kein HTTPS an); die Integration nur im vertrauenswürdigen lokalen Netz verwenden und den BEAAM-Port nicht ins Internet freigeben.
- **Einstellungen werden über eine feste Tabelle zugeordnet.** Bekannte Einstellungen bekommen passende Einheiten: Schwellwerte der Wärmepumpe (`POWER_THRESHOLD_*`) in W, Sperr- und Anlaufzeit (`LOCK_TIME`, `RAMP_UP_TIME`) in Sekunden. Einstellungen, die das Gateway neu meldet und die die Integration noch nicht kennt, werden weiterhin anhand ihres Werts erkannt, aber standardmäßig deaktiviert angelegt; sie lassen sich in den Entitäts-Einstellungen aktivieren. Bereits vorhandene Entitäten bleiben aktiv. Jede Einstellung erzeugt nur noch eine Entität (bisher konnte z. B. ein Schlüssel mit „POWER“ und dem Wert `true` gleichzeitig Schalter und Zahl werden).
- Neu in der Tabelle laut offizieller BEAAM-API-Doku: Einspeise-Priorisierung (`GRID_FEED_IN_PRIORITIZATION_ENABLED` als Schalter, `GRID_FEED_IN_PRIORITIZATION_POWER` in W). Einstellungen, deren Wert das Gateway als echten Boolean statt als Text `"true"`/`"false"` liefert, werden jetzt ebenfalls als Schalter erkannt.
- States und Einstellungen aller Geräte werden in einer gemeinsamen Runde parallel vom Gateway abgefragt statt in zwei Runden nacheinander. Ein Abfragezyklus dauert dadurch etwa halb so lang.
- Ist ein einzelnes Gerät (z. B. die Batterie) über das Gateway nicht abrufbar, erscheint jetzt einmalig eine Warnung mit Gerätename und Ursache im Log; sobald es wieder antwortet, eine Info. Bisher standen solche Fehler nur im Debug-Log, und Antworten mit HTTP-Fehlercode wurden gar nicht protokolliert. Weitere Fehler desselben Geräts landen weiterhin nur im Debug-Log. Geräte ohne Einstellungen (HTTP 404 auf `/settings`) gelten nicht als Fehler.

### Intern
- Neuer CI-Workflow „Lint & Test“: `ruff check` und `pytest` laufen bei jedem Push und Pull Request (Tests mit einer älteren und der aktuellen Home Assistant Version). Ruff-Konfiguration in `pyproject.toml`; der bestehende Code wurde entsprechend bereinigt (u. a. moderne Typschreibweise `dict`/`X | None`, keine Leerzeichen am Zeilenende), ohne Verhaltensänderung.

## 1.1.3

### Behoben
- Vorbereitung auf Home Assistant 2027.8: Geräte verweisen auf das BEAAM Gateway jetzt über `via_device_id` statt über den veralteten Parameter `via_device`. Die Warnung „calls `device_registry.async_get_or_create` with a deprecated `via_device` parameter“ im Log entfällt. Auf Home Assistant vor 2026.8 wird weiterhin `via_device` verwendet.
- Die Migration des Gateway-Geräts aus Version 1.0.x nutzt ab Home Assistant 2026.8 die neue Geräte-Abfrage pro Eintrag (`async_get_device_by_identifier`) statt des veralteten `async_get_device`.

## 1.1.2

### Behoben
- Vom Gateway berechnete Energie-Bilanzen (`ENERGY_CONSUMED_CALC`, `ENERGY_APPLIANCES` u. ä.) können sinken oder negativ sein. Sie werden jetzt mit `state_class: total` statt `total_increasing` angelegt, damit Home Assistant einen Rückgang nicht als Zähler-Reset wertet und die Statistiken nicht verfälscht.

## 1.1.1

### Behoben
- Ladezustands-Sensoren mit dem Schlüssel `STATE_OF_CHARGE` (z. B. „Batterie Master State Of Charge“) erhalten jetzt die Geräteklasse *Batterie* und sind im Energie-Dashboard als Ladezustand auswählbar. Bisher wurde nur `SOC` erkannt ([#1](https://github.com/MovingLlama/neoom/issues/1)).

### Neu
- Standortweite Energiefluss-Werte des BEAAM Gateways (z. B. Hausverbrauch, Netz, Speicher, PV, Gesamt-SoC) werden – sofern das Gateway sie in seiner Konfiguration meldet – als Sensoren am Gerät „BEAAM Gateway“ angelegt. Damit ist der Gesamtverbrauch wie in der neoom App („Stromverbrauch allgemein“) in Home Assistant verfügbar ([#1](https://github.com/MovingLlama/neoom/issues/1)).

## 1.1.0

### ⚠️ Breaking Changes
- **Ein BEAAM Gateway-Gerät pro Site.** Bisher teilten sich alle Sites in einer Home Assistant Instanz ein gemeinsames Gerät „BEAAM Gateway“. Jetzt erhält jede Site (= jeder Integrationseintrag) ein eigenes Gateway-Gerät mit der Kennung `beaam_<site_id>`.
  - **Nur eine Site eingerichtet:** keine Auswirkung. Gerät, Bereich und Entity-IDs bleiben erhalten; das Gerät heißt künftig „BEAAM Gateway (<Site-Name>)“, sofern nicht selbst umbenannt.
  - **Mehrere Sites eingerichtet:** Das bisher gemeinsame Gerät bleibt bei einer Site, die anderen Sites erhalten ein neues Gateway-Gerät. Bitte Bereich und ggf. Dashboards/Automationen prüfen, die sich auf das Gateway-Gerät beziehen.
- **Ingest-Entitäten nur noch für Generic Devices.** Die standardmäßig deaktivierten „(Ingest)“-Number-/Select-Entitäten werden nur noch für Geräte vom Typ *generic* angelegt. Deaktivierte Ingest-Entitäten anderer Geräte werden automatisch entfernt; selbst aktivierte bleiben erhalten. Der Dienst `neoom.ingest_state` ist unverändert.

### Behoben
- Neue Zugangsdaten aus „Erneut authentifizieren“ und „Neu konfigurieren“ wurden ignoriert, sobald einmal die Optionen (Zahnrad) gespeichert waren. Zugangsdaten werden jetzt nur noch an einer Stelle gespeichert; bestehende Einträge werden automatisch migriert.
- Neu im neoom-System angelegte Geräte erschienen erst nach einem Neuladen der Integration. Die Gerätestruktur wird jetzt stündlich neu geladen.

### Neu
- Geräte, die das BEAAM Gateway nicht mehr meldet, können in Home Assistant gelöscht werden.
- Bei der Einrichtung werden bereits eingebundene Sites nicht mehr angeboten, und dasselbe BEAAM Gateway kann nicht doppelt eingebunden werden.
- Automatisierte Tests (`pytest`, siehe `requirements_test.txt`).
