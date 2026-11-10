"""Sensor Plattform für neoom AI.

Diese Datei definiert die "nur-lesen" Sensoren, die Daten aus der neoom AI Cloud
und dem lokalen BEAAM Gateway in Home Assistant anzeigen.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    EntityCategory,
    UnitOfApparentPower,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfFrequency,
    UnitOfPower,
    UnitOfPressure,
    UnitOfReactivePower,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import NeoomCloudCoordinator, NeoomConfigEntry, NeoomLocalCoordinator
from .helpers import (
    array_item_type,
    classify_setting,
    find_state,
    get_friendly_thing_name,
)

# Pseudo-Thing-ID für die standortweiten Energiefluss-Datenpunkte des BEAAM Gateways.
# Entspricht dem Präfix, unter dem der Koordinator die Werte aus site/state ablegt.
ENERGY_FLOW_ID = "energyFlow"

# Schlüssel-Bestandteile, die einen Batterie-Ladezustand kennzeichnen.
BATTERY_LEVEL_INDICATORS = ("SOC", "STATE_OF_CHARGE")

# Schlüssel-Bestandteile von Energiewerten, die das Gateway aus anderen Zählern
# berechnet (z.B. ENERGY_CONSUMED_CALC, ENERGY_APPLIANCES). Solche Bilanzen können
# sinken oder negativ sein und sind daher keine stetig steigenden Zählerstände.
DERIVED_ENERGY_INDICATORS = ("_CALC", "APPLIANCES")

# Energiefluss-Werte, die das Gateway nur mit einem eigenen Verbrauchszähler liefert. Ohne ihn
# bleiben sie leer; die Entitäten werden daher standardmäßig deaktiviert angelegt.
METER_ONLY_ENERGY_FLOW_KEYS = ("POWER_CONSUMPTION", "ENERGY_CONSUMED", "POWER_GRID_REMAINING")

# Anteile (0…1) im Energiefluss, z. B. FRACTION_PV_TO_CONSUMPTION. Sie werden in Prozent angezeigt.
FRACTION_PREFIX = "FRACTION_"

# Anzeige von Text-Arrays (z. B. ERROR_CODES), wenn die Liste leer ist.
EMPTY_LIST_STATE = "none"

# Maximale Länge eines Sensorzustands in Home Assistant.
MAX_STATE_LENGTH = 255

# Einstellungen aus der offiziellen BEAAM-API, für die es keine passende Eingabe-Plattform gibt
# (Format der Werte nicht dokumentiert). Sie werden nur lesend als Sensor angezeigt.
READ_ONLY_SETTINGS = ("EV_SELECTED", "GRID_FEED_IN_PRIORITIZATION_TIMES")


@dataclass(frozen=True)
class CloudSensorSpec:
    """Beschreibt einen Sensor aus den Daten der neoom AI Cloud."""

    key: str
    name: str
    data_path: str  # "site" (Stammdaten/Tarife) oder "flow" (energy-flow/latest)
    unit: str | None = None
    icon: str | None = None
    device_class: SensorDeviceClass | None = None
    state_class: SensorStateClass | None = None
    diagnostic: bool = False
    enabled_default: bool = True
    # Feld in denselben Daten, das als Attribut "total" angezeigt wird (z. B. Gesamtzahl der Geräte)
    total_key: str | None = None


CLOUD_SENSORS: tuple[CloudSensorSpec, ...] = (
    CloudSensorSpec(
        "electricity_price", "Electricity Price", "site",
        unit="ct/kWh", icon="mdi:currency-eur", state_class=SensorStateClass.MEASUREMENT,
    ),
    CloudSensorSpec(
        "feed_in_tariff", "Feed-in Tariff", "site",
        unit="ct/kWh", icon="mdi:cash-plus", state_class=SensorStateClass.MEASUREMENT,
    ),
    CloudSensorSpec("gateways_online_state", "Gateway Status", "flow", icon="mdi:router-network"),
    CloudSensorSpec(
        "co2_factor", "CO2 Factor", "site",
        unit="kg/kWh", icon="mdi:molecule-co2", state_class=SensorStateClass.MEASUREMENT,
    ),
    CloudSensorSpec(
        "max_network_utilization", "Max Network Utilization", "site",
        unit=UnitOfPower.WATT, device_class=SensorDeviceClass.POWER, state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:transmission-tower",
    ),
    # Wie viele Geräte je Gruppe die Cloud gerade erreicht; die Gesamtzahl steht im Attribut "total"
    *(
        CloudSensorSpec(
            f"{group}_online_count", f"{label} Online", "flow",
            icon="mdi:lan-connect", state_class=SensorStateClass.MEASUREMENT,
            diagnostic=True, enabled_default=False, total_key=f"{group}_total_count",
        )
        for group, label in (
            ("producers", "Producers"),
            ("consumers", "Consumers"),
            ("storages", "Storages"),
            ("heatings", "Heatings"),
            ("charging_points", "Charging Points"),
            ("grids", "Grids"),
        )
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: NeoomConfigEntry,
    async_add_entities: Callable[[list[SensorEntity]], None],
) -> None:
    """Richtet die Sensor-Plattform basierend auf dem Konfigurationseintrag ein.

    Diese Methode wird von Home Assistant aufgerufen, um Entitäten zu registrieren.
    """

    # Hole die Koordinatoren, die wir in __init__.py am Eintrag abgelegt haben
    cloud_coordinator = entry.runtime_data.cloud
    local_coordinator = entry.runtime_data.local

    # --- CLOUD SENSOREN ---
    # Diese Sensoren stehen fest, da wir wissen, welche Daten die Cloud zurückgibt.
    entities: list[SensorEntity] = [NeoomCloudSensor(cloud_coordinator, spec) for spec in CLOUD_SENSORS]

    async_add_entities(entities)

    # --- LOKALE SENSOREN (Dynamisch) ---
    # Da das BEAAM Gateway je nach Standort unterschiedliche Geräte
    # (Wechselrichter, Speicher, E-Ladestation) angebunden hat,
    # generieren wir diese Sensoren dynamisch anhand der BEAAM Konfiguration
    # und überwachen spätere Updates.
    known_sensor_ids: set[str] = set()

    @callback
    def _async_check_entities() -> None:
        """Prüft auf neu verfügbare Datenpunkte und legt Sensor-Entitäten an."""
        if not local_coordinator.data:
            return

        beaam_config = local_coordinator.data.get("config", {})
        if not beaam_config or not isinstance(beaam_config, dict):
            return

        things = beaam_config.get("things", {})
        if not isinstance(things, dict):
            return

        new_entities: list[SensorEntity] = []
        state_map: dict[str, Any] = local_coordinator.data.get("states", {})

        # Standortweite Energiefluss-Werte (z.B. Hausverbrauch, Netzbezug, Gesamt-SoC).
        # Sie gehören zu keinem einzelnen Gerät und werden dem BEAAM Gateway zugeordnet.
        energy_flow = beaam_config.get("energyFlow")
        if isinstance(energy_flow, dict):
            ef_datapoints = energy_flow.get("dataPoints", {})
            if isinstance(ef_datapoints, dict):
                for dp_id, dp_data in ef_datapoints.items():
                    if not dp_data or not isinstance(dp_data, dict):
                        continue
                    if dp_data.get("dataType", "") not in ["NUMBER", "STRING"]:
                        continue
                    sensor = NeoomEnergyFlowSensor(
                        coordinator=local_coordinator,
                        dp_id=dp_id,
                        dp_data=dp_data,
                    )
                    if sensor.unique_id not in known_sensor_ids:
                        known_sensor_ids.add(sensor.unique_id)
                        new_entities.append(sensor)

        for thing_id, thing_data in things.items():
            if not thing_data or not isinstance(thing_data, dict):
                continue

            datapoints: dict[str, Any] = thing_data.get("dataPoints", {})
            if not isinstance(datapoints, dict):
                continue

            for dp_id, dp_data in datapoints.items():
                if not dp_data or not isinstance(dp_data, dict):
                    continue

                dtype: str = dp_data.get("dataType", "")
                item_type = array_item_type(dtype)

                # Wir erstellen Sensoren für Zahlen (Leistung, Prozente) und Strings (Betriebsmodi)
                if dtype in ["NUMBER", "STRING"]:
                    unique_id = f"{thing_id}_{dp_id}"
                    if unique_id not in known_sensor_ids:
                        known_sensor_ids.add(unique_id)
                        new_entities.append(
                            NeoomLocalSensor(
                                coordinator=local_coordinator,
                                thing_id=thing_id,
                                thing_data=thing_data,
                                dp_id=dp_id,
                                dp_data=dp_data,
                            )
                        )
                elif item_type == "STRING":
                    # Text-Listen (z. B. ERROR_CODES) als ein Sensor mit allen Einträgen
                    unique_id = f"{thing_id}_{dp_id}"
                    if unique_id not in known_sensor_ids:
                        known_sensor_ids.add(unique_id)
                        new_entities.append(
                            NeoomStringArraySensor(
                                coordinator=local_coordinator,
                                thing_id=thing_id,
                                thing_data=thing_data,
                                dp_id=dp_id,
                                dp_data=dp_data,
                            )
                        )
                elif item_type == "NUMBER":
                    # Zahlen-Listen (z. B. Spannung pro PV-String) als ein Sensor pro Eintrag. Wie viele
                    # Einträge es gibt, zeigt erst der aktuelle Zustand.
                    data_point = find_state(state_map, thing_id, dp_id, dp_data.get("key", ""))
                    values = data_point.get("value") if data_point else None
                    if not isinstance(values, list):
                        continue
                    for index in range(len(values)):
                        unique_id = f"{thing_id}_{dp_id}_{index}"
                        if unique_id not in known_sensor_ids:
                            known_sensor_ids.add(unique_id)
                            new_entities.append(
                                NeoomArrayItemSensor(
                                    coordinator=local_coordinator,
                                    thing_id=thing_id,
                                    thing_data=thing_data,
                                    dp_id=dp_id,
                                    dp_data=dp_data,
                                    index=index,
                                )
                            )

        # Einstellungen, für die es keine Eingabe-Plattform gibt, nur lesend anzeigen
        settings_map: dict[str, dict[str, Any]] = local_coordinator.data.get("settings", {})
        for thing_id, thing_data in things.items():
            thing_settings = settings_map.get(thing_id)
            if not isinstance(thing_data, dict) or not isinstance(thing_settings, dict):
                continue
            for key, val in thing_settings.items():
                spec, _known = classify_setting(key, val)
                if spec is not None:
                    continue
                unique_id = f"{thing_id}_{key}_setting"
                if unique_id not in known_sensor_ids:
                    known_sensor_ids.add(unique_id)
                    new_entities.append(
                        NeoomSettingSensor(
                            coordinator=local_coordinator,
                            thing_id=thing_id,
                            thing_data=thing_data,
                            setting_key=key,
                        )
                    )

        if new_entities:
            async_add_entities(new_entities)

    _async_check_entities()
    entry.async_on_unload(
        local_coordinator.async_add_listener(_async_check_entities)
    )


class NeoomCloudSensor(CoordinatorEntity, SensorEntity):
    """Repräsentation eines generischen Cloud-Sensors (z.B. Tarifdaten).

    Erbt von CoordinatorEntity, damit der Sensor automatisch aktualisiert wird,
    wenn der Koordinator neue Daten aus dem Internet lädt.
    """

    _attr_has_entity_name = True

    def __init__(self, coordinator: NeoomCloudCoordinator, spec: CloudSensorSpec) -> None:
        """Initialisiert den Cloud-Sensor."""
        super().__init__(coordinator)
        self._key = spec.key
        self._data_path = spec.data_path
        self._total_key = spec.total_key
        self._attr_native_unit_of_measurement = spec.unit
        self._attr_icon = spec.icon
        self._attr_device_class = spec.device_class
        self._attr_state_class = spec.state_class
        self._attr_entity_registry_enabled_default = spec.enabled_default
        if spec.diagnostic:
            self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_translation_key = spec.key
        self._attr_name = spec.name

        # Eindeutige ID ist entscheidend für Home Assistant, um die Entität wiederzuerkennen
        self._attr_unique_id = f"{coordinator.site_id}_{spec.key}"

    def _section(self) -> dict[str, Any]:
        """Liefert den Teil der Cloud-Daten ('site' oder 'flow'), aus dem der Sensor liest."""
        section = (self.coordinator.data or {}).get(self._data_path)
        return section if isinstance(section, dict) else {}

    @property
    def native_value(self) -> Any:
        """Gibt den aktuellen Zustand/Wert des Sensors zurück."""
        value = self._section().get(self._key)
        if isinstance(value, dict):
            # Zeitreihen-Werte liefert die Cloud als {"time": ..., "value": ...}
            value = value.get("value")
        return value

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Gibt zusätzliche Attribute für den Cloud-Sensor zurück."""
        attributes: dict[str, Any] = {
            "key": self._key,
            "data_path": self._data_path,
        }
        if self._total_key:
            attributes["total"] = self._section().get(self._total_key)
        return attributes

    @property
    def device_info(self) -> DeviceInfo:
        """Gibt Informationen zum virtuellen Cloud-Gerät zurück.

        Gruppiert die Cloud-Sensoren zusammen unter einem "Gerät" in der UI. Der Name enthält
        den Namen der Site, damit sich mehrere Sites unterscheiden lassen.
        """
        site_name = self.coordinator.site_name
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.site_id)},
            name=f"neoom AI Cloud ({site_name})" if site_name else "neoom AI Cloud Site",
            manufacturer="neoom",
            model="Cloud API",
        )


class NeoomLocalSensor(CoordinatorEntity, SensorEntity):
    """Repräsentation eines lokalen BEAAM Sensors (z.B. Leistung, Temperatur)."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: NeoomLocalCoordinator,
        thing_id: str,
        thing_data: dict[str, Any],
        dp_id: str,
        dp_data: dict[str, Any],
    ) -> None:
        """Initialisiert den lokalen Sensor."""
        super().__init__(coordinator)

        self._thing_id = thing_id
        self._thing_type: str = thing_data.get("type", "Unknown")
        self._dp_id = dp_id
        self._key: str = dp_data.get("key", "")
        self._uom_raw: str = dp_data.get("unitOfMeasure", "")
        if dp_data.get("dataType") == "STRING":
            # Texte haben weder Einheit noch Geräte- oder Statusklasse (die setzen Zahlen voraus)
            self._uom_raw = ""

        beaam_config = coordinator.data.get("config", {}) if coordinator.data else {}
        self._friendly_thing_name = get_friendly_thing_name(beaam_config, thing_id, self._thing_type)
        friendly_dp_name = self._key.replace("_", " ").title()

        self._attr_name = friendly_dp_name
        self._attr_unique_id = f"{thing_id}_{dp_id}"

        # Weise HA-spezifische Device Classes (Typ des Sensors, z.B. Leistung)
        # und State Classes (Verhalten über Zeit, z.B. kumulativ) zu
        self._attr_device_class = self._map_device_class(self._key, self._uom_raw)
        self._attr_state_class = self._map_state_class(self._key, self._uom_raw)

        # Leite die richtige Einheit (z.B. kW, W) aus der rohen API-Einheit ab
        self._attr_native_unit_of_measurement = self._map_unit(self._uom_raw)

        # Anteile (0…1) ohne eigene Einheit werden in Prozent angezeigt
        self._is_fraction = self._key.startswith(FRACTION_PREFIX) and self._attr_native_unit_of_measurement is None
        if self._is_fraction:
            self._attr_native_unit_of_measurement = PERCENTAGE
            self._attr_state_class = SensorStateClass.MEASUREMENT
            self._attr_suggested_display_precision = 1

        # Initialen Status beim Erstellen setzen
        self._update_state()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Wird von der CoordinatorEntity-Basisklasse aufgerufen, wenn neue Daten ankommen.

        Wir aktualisieren unseren internen Wert und leiten dann das Update an Home Assistant weiter.
        """
        self._update_state()
        super()._handle_coordinator_update()

    def _update_state(self) -> None:
        """Liest den aktuellen Wert aus den Coordinator-Daten aus und setzt ihn als Status."""
        if not self.coordinator.data:
            self._attr_native_value = None
            return

        data_point = self._current_data_point()

        if data_point:
            raw_value = data_point.get("value")

            # Gib Nummern als float, Texte als string zurück.
            # Wir verzichten hier bewusst auf manuelle Skalierungs-Magie (wie Kilo/Mega präfixe).
            # Home Assistant handhabt natives Skalieren in der UI automatisch viel besser,
            # wenn die Einheit und Device Class stimmen.
            if self._key == "OPERATING_MODE_SG_READY":
                val_str = str(raw_value).lower() if raw_value is not None else ""
                if val_str in ["65636", "0", "100", "2"]:
                    self._attr_native_value = "Normal (Mode 2)"
                elif val_str == "1":
                    self._attr_native_value = "Sperre (Mode 1)"
                elif val_str == "3":
                    self._attr_native_value = "Empfehlung (Mode 3)"
                elif val_str == "4":
                    self._attr_native_value = "Fest EIN (Mode 4)"
                else:
                    self._attr_native_value = raw_value
            elif self._is_fraction and isinstance(raw_value, (int, float)):
                self._attr_native_value = float(raw_value) * 100
            elif raw_value is not None and isinstance(raw_value, (int, float)):
                self._attr_native_value = float(raw_value)
            else:
                self._attr_native_value = raw_value
        else:
            self._attr_native_value = None

    def _current_data_point(self) -> dict[str, Any] | None:
        """Liefert den aktuellen Zustand dieses Datenpunkts aus den Coordinator-Daten."""
        if not self.coordinator.data:
            return None
        state_map: dict[str, Any] = self.coordinator.data.get("states", {})
        return find_state(state_map, self._thing_id, self._dp_id, self._key)

    @property
    def device_info(self) -> DeviceInfo:
        """Gibt Informationen zum zugrundeliegenden Gerät zurück.

        Verknüpft diesen Sensor mit dem physischen Gerät (z.B. Wechselrichter).
        'via_device' zeigt an, dass die Kommunikation über das BEAAM Gateway läuft.
        """
        return DeviceInfo(
            identifiers={(DOMAIN, self._thing_id)},
            name=f"neoom {getattr(self, '_friendly_thing_name', self._thing_type)}",
            manufacturer="neoom",
            model=self._thing_type,
            **self.coordinator.gateway_link,
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Gibt spezifische Attribute für diesen Datenpunkt zurück."""
        return {
            "thing_id": self._thing_id,
            "datapoint_id": self._dp_id,
            "key": self._key,
        }

    def _map_unit(self, unit_str: str) -> str | None:
        """Konvertiert die BEAAM String-Einheit in die offizielle Home Assistant Konstante."""
        if not unit_str or unit_str.lower() in ["none", "null"]:
            return None

        # Leistung (Power)
        if unit_str == "W":
            return UnitOfPower.WATT
        if unit_str == "kW":
            return UnitOfPower.KILO_WATT
        if unit_str == "MW":
            return UnitOfPower.MEGA_WATT
        if unit_str == "GW":
            return UnitOfPower.GIGA_WATT

        # Energie (Energy)
        if unit_str == "Wh":
            return UnitOfEnergy.WATT_HOUR
        if unit_str == "kWh":
            return UnitOfEnergy.KILO_WATT_HOUR
        if unit_str == "MWh":
            return UnitOfEnergy.MEGA_WATT_HOUR
        if unit_str == "GWh":
            return UnitOfEnergy.GIGA_WATT_HOUR

        # Elektrische Werte
        if unit_str == "V":
            return UnitOfElectricPotential.VOLT
        if unit_str == "A":
            return UnitOfElectricCurrent.AMPERE
        if unit_str == "Hz":
            return UnitOfFrequency.HERTZ
        if unit_str == "VAr":
            return UnitOfReactivePower.VOLT_AMPERE_REACTIVE
        if unit_str == "VA":
            return UnitOfApparentPower.VOLT_AMPERE
        if unit_str == "Pa":
            return UnitOfPressure.PA

        # Temperatur
        if unit_str in ["C", "°C"]:
            return UnitOfTemperature.CELSIUS
        if unit_str == "K":
            return UnitOfTemperature.KELVIN

        # Sonstiges
        if unit_str == "%":
            return PERCENTAGE
        if unit_str == "s":
            return UnitOfTime.SECONDS
        if unit_str == "h":
            return UnitOfTime.HOURS

        # Fallback auf den rohen String, wenn unbekannt
        return unit_str

    def _map_device_class(self, key: str, unit: str) -> SensorDeviceClass | None:
        """Weist basierend auf dem Datentyp / der Einheit die richtige Home Assistant Sensor-Klasse zu.
        Dies beeinflusst die Darstellung und die verfügbaren Einheitenumrechnungen in der UI.
        """
        if unit in ["W", "kW", "MW", "GW"]:
            return SensorDeviceClass.POWER
        if unit in ["Wh", "kWh", "MWh", "GWh"]:
            return SensorDeviceClass.ENERGY
        if unit == "V":
            return SensorDeviceClass.VOLTAGE
        if unit == "A":
            return SensorDeviceClass.CURRENT
        if unit == "Hz":
            return SensorDeviceClass.FREQUENCY
        if unit == "VAr":
            return SensorDeviceClass.REACTIVE_POWER
        if unit == "VA":
            return SensorDeviceClass.APPARENT_POWER
        if unit == "Pa":
            return SensorDeviceClass.PRESSURE
        # Temperatur und Dauer nur anhand der Einheit: Schlüssel wie MAX_CELL_TEMPERATURE_NUMBER
        # (Nummer einer Zelle) oder CHARGING_PROCESS_START_TIME (Zeitpunkt) sind keine Messwerte.
        if unit in ["C", "K", "°C"]:
            return SensorDeviceClass.TEMPERATURE
        if unit in ["s", "h"]:
            return SensorDeviceClass.DURATION
        if unit == "%" and any(ind in key.upper() for ind in BATTERY_LEVEL_INDICATORS):
            # SOC bzw. STATE_OF_CHARGE steht für den Batterie-Ladezustand. Die Geräteklasse
            # "Batterie" ist nötig, damit der Sensor im Energie-Dashboard auswählbar ist.
            return SensorDeviceClass.BATTERY

        return None

    def _map_state_class(self, key: str, unit: str) -> SensorStateClass | None:
        """Bestimmt das Langzeit-Aufzeichnungsverhalten (Statistics) des Sensors in HA."""
        # Wenn es sich um eine Zahl ohne Einheit (None) handelt oder einen Text-Status
        if not unit or unit.lower() in ["none", "null"]:
            return None

        # Ausschluss von Nicht-Energiewerten: Leistung, Spannung, Strom, Frequenz, Temperatur, Zeit, Prozent
        if unit in ["%", "W", "kW", "MW", "GW", "V", "A", "Hz", "C", "K", "°C", "s", "h", UnitOfTemperature.CELSIUS, UnitOfTemperature.KELVIN, UnitOfTime.SECONDS, UnitOfTime.HOURS]:
            return SensorStateClass.MEASUREMENT

        # Prüfung für Energiewerte (Wh, kWh, MWh, GWh)
        if unit in ["Wh", "kWh", "MWh", "GWh"]:
            key_upper = key.upper()
            # Nicht-kumulative Energiewerte (z.B. gespeicherte Batterieenergie, Restkapazität, Limits)
            # stellen einen aktuellen Messwert dar und dürfen NICHT als TOTAL_INCREASING markiert werden,
            # da ein Absinken des Wertes sonst als Zähler-Reset interpretiert würde und Statistiken verfälscht.
            non_cumulative_indicators = [
                "STORED",
                "STORAGE",
                "USABLE",
                "RESERVE",
                "CAPACITY",
                "REMAINING",
                "CONTENT",
                "TARGET",
                "LIMIT",
                "CURRENT",
                "LEVEL",
                "SOC",
                "STATE_OF_CHARGE",
            ]
            if any(indicator in key_upper for indicator in non_cumulative_indicators):
                return SensorStateClass.MEASUREMENT

            # Berechnete Bilanzen: Summe über die Zeit, aber ohne Reset-Erkennung bei sinkenden Werten
            if any(indicator in key_upper for indicator in DERIVED_ENERGY_INDICATORS):
                return SensorStateClass.TOTAL

            # Zählerstände / kumulative Energiemengen (z.B. erzeugt, verbraucht, eingespeist)
            return SensorStateClass.TOTAL_INCREASING

        # Normalfall für sonstige Messwerte
        return SensorStateClass.MEASUREMENT


class NeoomEnergyFlowSensor(NeoomLocalSensor):
    """Standortweiter Energiefluss-Wert des BEAAM Gateways (z.B. Hausverbrauch).

    Diese Werte entsprechen der Energiefluss-Übersicht der neoom App und werden
    dem BEAAM Gateway-Gerät der Site zugeordnet.
    """

    def __init__(
        self,
        coordinator: NeoomLocalCoordinator,
        dp_id: str,
        dp_data: dict[str, Any],
    ) -> None:
        """Initialisiert den Energiefluss-Sensor."""
        super().__init__(
            coordinator=coordinator,
            thing_id=ENERGY_FLOW_ID,
            thing_data={"type": "ENERGY_FLOW"},
            dp_id=dp_id,
            dp_data=dp_data,
        )
        # Die Gateway-Kennung enthält die Site-ID, damit mehrere Sites nicht kollidieren.
        self._attr_unique_id = f"{coordinator.gateway_identifier[1]}_energy_flow_{dp_id}"
        if self._key in METER_ONLY_ENERGY_FLOW_KEYS:
            # Betrifft nur neu angelegte Entitäten; bestehende behalten ihren Status
            self._attr_entity_registry_enabled_default = False

    @property
    def device_info(self) -> DeviceInfo:
        """Ordnet den Sensor dem (bereits registrierten) BEAAM Gateway der Site zu."""
        return DeviceInfo(identifiers={self.coordinator.gateway_identifier})


class NeoomArrayItemSensor(NeoomLocalSensor):
    """Ein Eintrag eines Zahlen-Arrays, z. B. die Spannung eines PV-Strings (VOLTAGES[0])."""

    def __init__(
        self,
        coordinator: NeoomLocalCoordinator,
        thing_id: str,
        thing_data: dict[str, Any],
        dp_id: str,
        dp_data: dict[str, Any],
        index: int,
    ) -> None:
        """Initialisiert den Sensor für den Eintrag mit dem Index index (ab 0)."""
        self._index = index
        super().__init__(coordinator, thing_id, thing_data, dp_id, dp_data)
        # Anzeige ab 1, z. B. "Voltages 1" für den ersten PV-String
        self._attr_name = f"{self._attr_name} {index + 1}"
        self._attr_unique_id = f"{thing_id}_{dp_id}_{index}"

    def _update_state(self) -> None:
        """Liest den Eintrag self._index aus der Liste des Datenpunkts."""
        data_point = self._current_data_point()
        values = data_point.get("value") if data_point else None
        value = values[self._index] if isinstance(values, list) and self._index < len(values) else None
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            self._attr_native_value = float(value)
        else:
            self._attr_native_value = None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Ergänzt die Attribute um den Index im Array."""
        return {**super().extra_state_attributes, "index": self._index}


class NeoomStringArraySensor(NeoomLocalSensor):
    """Eine Text-Liste, z. B. ERROR_CODES. Der Zustand zeigt alle Einträge durch Komma getrennt."""

    def __init__(
        self,
        coordinator: NeoomLocalCoordinator,
        thing_id: str,
        thing_data: dict[str, Any],
        dp_id: str,
        dp_data: dict[str, Any],
    ) -> None:
        """Initialisiert den Sensor (ohne Einheit und Geräteklasse)."""
        super().__init__(coordinator, thing_id, thing_data, dp_id, dp_data)
        self._attr_device_class = None
        self._attr_state_class = None
        self._attr_native_unit_of_measurement = None

    def _update_state(self) -> None:
        """Fasst die Einträge der Liste zu einem Text zusammen."""
        data_point = self._current_data_point()
        values = data_point.get("value") if data_point else None
        if not isinstance(values, list):
            self._values: list[Any] = []
            self._attr_native_value = None
            return
        self._values = values
        text = ", ".join(str(value) for value in values) or EMPTY_LIST_STATE
        self._attr_native_value = text[:MAX_STATE_LENGTH]

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Ergänzt die Attribute um die vollständige Liste."""
        return {**super().extra_state_attributes, "values": self._values}


class NeoomSettingSensor(CoordinatorEntity[NeoomLocalCoordinator], SensorEntity):
    """Eine Einstellung des Gateways, die nur angezeigt wird (z. B. EV_SELECTED).

    Für diese Einstellungen gibt es keine passende Eingabe-Plattform. Außerhalb von
    READ_ONLY_SETTINGS (offizielle API) sind die Entitäten standardmäßig deaktiviert.
    """

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:cog-outline"

    def __init__(
        self,
        coordinator: NeoomLocalCoordinator,
        thing_id: str,
        thing_data: dict[str, Any],
        setting_key: str,
    ) -> None:
        """Initialisiert den Sensor für die Einstellung setting_key."""
        super().__init__(coordinator)
        self._thing_id = thing_id
        self._thing_type: str = thing_data.get("type", "Unknown")
        self._setting_key = setting_key

        beaam_config = coordinator.data.get("config", {}) if coordinator.data else {}
        self._friendly_thing_name = get_friendly_thing_name(beaam_config, thing_id, self._thing_type)

        self._attr_name = setting_key.replace("_", " ").title()
        self._attr_unique_id = f"{thing_id}_{setting_key}_setting"
        self._attr_entity_registry_enabled_default = setting_key in READ_ONLY_SETTINGS

    @property
    def native_value(self) -> str | None:
        """Gibt den aktuellen Wert der Einstellung als Text zurück."""
        if not self.coordinator.data:
            return None
        value = self.coordinator.data.get("settings", {}).get(self._thing_id, {}).get(self._setting_key)
        if value is None:
            return None
        return str(value)[:MAX_STATE_LENGTH]

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Gibt spezifische Attribute für diese Einstellung zurück."""
        return {"thing_id": self._thing_id, "key": self._setting_key}

    @property
    def device_info(self) -> DeviceInfo:
        """Verknüpfung der Entität mit dem physischen Gerät (Thing) im Device Registry."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._thing_id)},
            name=f"neoom {self._friendly_thing_name}",
            manufacturer="neoom",
            model=self._thing_type,
            **self.coordinator.gateway_link,
        )
