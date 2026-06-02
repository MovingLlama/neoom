# API-Schnittstellen-Analyse
# Da der Shell-Runner temporär nicht verfügbar war, wurden die API-Definitionen direkt
# aus den offiziellen OpenAPI-Dokumenten der neoom Entwicklerplattform (developer.neoom.com) extrahiert.
#
# Wichtige Links zur API-Dokumentation:
# - Konzepte & Begriffe: https://developer.neoom.com/reference/concepts-terms-1.md
# - site/configuration: https://developer.neoom.com/reference/sitecontroller_getsiteconfiguration.md
# - site/state: https://developer.neoom.com/reference/sitecontroller_getsitestate.md
# - things/{thingId}/states: https://developer.neoom.com/reference/thingscontroller_getcurrentstates.md
#
# Erkenntnisse:
# 1. Ladestationen / Wallboxen:
#    Es gibt keinen Datenpunkt für ein ausgewiesenes E-Fahrzeug.
#    Die relevanten Datenpunkte der API sind:
#    - CP_STATE_CODE, EV_STATE_CODE, LAST_RFID_CARD, CHARGING_PROCESS_ID, START_STOP_CHARGING.
#    Fahrzeugzuweisung kann in Home Assistant über die Zuordnung der `LAST_RFID_CARD`-UID gelöst werden.
#
# 2. Wärmepumpen / SG Ready:
#    - Key: `OPERATING_MODE_SG_READY` (dataType: STRING, Werte: "1", "2", "3", "4" für die jeweiligen Betriebsmodi).
#    - Ingest-Steuerung via `neoom.ingest_state` Service oder über die neu implementierte `NeoomIngestSelect` Entität.
