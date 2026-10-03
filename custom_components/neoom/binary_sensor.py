"""Binary-Sensor Plattform für neoom AI.

Diese Datei legt Binärsensoren für Ja/Nein-Datenpunkte des lokalen BEAAM Gateways an,
z. B. die Verbindung eines Geräts (CONNECTION) oder ob der Notstrombetrieb aktiv ist
(EPS_MODE_ACTIVE). Listen von Ja/Nein-Werten (z. B. CONNECTIONS pro PV-String) ergeben
einen Binärsensor pro Eintrag.
"""

from collections.abc import Callable
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import NeoomConfigEntry, NeoomLocalCoordinator
from .helpers import array_item_type, find_state, get_friendly_thing_name, parse_bool

# Schlüssel, die die Verbindung eines Geräts beschreiben (Geräteklasse "Konnektivität").
CONNECTIVITY_KEYS = ("CONNECTION", "CONNECTIONS")

# Bekannte Schlüssel mit eigenem Symbol.
KEY_ICONS: dict[str, str] = {
    "EPS_MODE_ACTIVE": "mdi:power-plug-battery",
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: NeoomConfigEntry,
    async_add_entities: Callable[[list[BinarySensorEntity]], None],
) -> None:
    """Richtet die Binary-Sensor-Plattform basierend auf dem Konfigurationseintrag ein."""
    local_coordinator = entry.runtime_data.local

    known_ids: set[str] = set()

    @callback
    def _async_check_entities() -> None:
        """Prüft auf neu verfügbare Ja/Nein-Datenpunkte und legt Binärsensoren an."""
        if not local_coordinator.data:
            return

        beaam_config = local_coordinator.data.get("config", {})
        if not beaam_config or not isinstance(beaam_config, dict):
            return

        things = beaam_config.get("things", {})
        if not isinstance(things, dict):
            return

        state_map: dict[str, Any] = local_coordinator.data.get("states", {})
        new_entities: list[BinarySensorEntity] = []

        for thing_id, thing_data in things.items():
            if not thing_data or not isinstance(thing_data, dict):
                continue

            datapoints = thing_data.get("dataPoints", {})
            if not isinstance(datapoints, dict):
                continue

            for dp_id, dp_data in datapoints.items():
                if not dp_data or not isinstance(dp_data, dict):
                    continue

                dtype: str = dp_data.get("dataType", "")
                if dtype == "BOOLEAN":
                    indices: list[int | None] = [None]
                elif array_item_type(dtype) == "BOOLEAN":
                    # Wie viele Einträge es gibt, zeigt erst der aktuelle Zustand
                    data_point = find_state(state_map, thing_id, dp_id, dp_data.get("key", ""))
                    values = data_point.get("value") if data_point else None
                    if not isinstance(values, list):
                        continue
                    indices = list(range(len(values)))
                else:
                    continue

                for index in indices:
                    unique_id = f"{thing_id}_{dp_id}" if index is None else f"{thing_id}_{dp_id}_{index}"
                    if unique_id in known_ids:
                        continue
                    known_ids.add(unique_id)
                    new_entities.append(
                        NeoomLocalBinarySensor(
                            coordinator=local_coordinator,
                            thing_id=thing_id,
                            thing_data=thing_data,
                            dp_id=dp_id,
                            dp_data=dp_data,
                            index=index,
                        )
                    )

        if new_entities:
            async_add_entities(new_entities)

    _async_check_entities()
    entry.async_on_unload(local_coordinator.async_add_listener(_async_check_entities))


class NeoomLocalBinarySensor(CoordinatorEntity[NeoomLocalCoordinator], BinarySensorEntity):
    """Ein Ja/Nein-Datenpunkt eines Geräts (oder ein Eintrag einer Ja/Nein-Liste)."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: NeoomLocalCoordinator,
        thing_id: str,
        thing_data: dict[str, Any],
        dp_id: str,
        dp_data: dict[str, Any],
        index: int | None = None,
    ) -> None:
        """Initialisiert den Binärsensor; index ist bei Listen der Eintrag (ab 0)."""
        super().__init__(coordinator)
        self._thing_id = thing_id
        self._thing_type: str = thing_data.get("type", "Unknown")
        self._dp_id = dp_id
        self._key: str = dp_data.get("key", "")
        self._index = index

        beaam_config = coordinator.data.get("config", {}) if coordinator.data else {}
        self._friendly_thing_name = get_friendly_thing_name(beaam_config, thing_id, self._thing_type)

        name = self._key.replace("_", " ").title()
        if index is None:
            self._attr_name = name
            self._attr_unique_id = f"{thing_id}_{dp_id}"
        else:
            # Anzeige ab 1, z. B. "Connections 1" für den ersten PV-String
            self._attr_name = f"{name} {index + 1}"
            self._attr_unique_id = f"{thing_id}_{dp_id}_{index}"

        if self._key in CONNECTIVITY_KEYS:
            self._attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
            self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_icon = KEY_ICONS.get(self._key)

    @property
    def is_on(self) -> bool | None:
        """Gibt den aktuellen Wert zurück (None, wenn das Gateway keinen Wert liefert)."""
        if not self.coordinator.data:
            return None
        state_map: dict[str, Any] = self.coordinator.data.get("states", {})
        data_point = find_state(state_map, self._thing_id, self._dp_id, self._key)
        if not data_point:
            return None
        value = data_point.get("value")
        if self._index is not None:
            if not isinstance(value, list) or self._index >= len(value):
                return None
            value = value[self._index]
        return parse_bool(value)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Gibt spezifische Attribute für diesen Datenpunkt zurück."""
        attributes: dict[str, Any] = {
            "thing_id": self._thing_id,
            "datapoint_id": self._dp_id,
            "key": self._key,
        }
        if self._index is not None:
            attributes["index"] = self._index
        return attributes

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
