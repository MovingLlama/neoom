# Changelog

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
