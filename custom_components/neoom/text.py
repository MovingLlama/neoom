"""Text Plattform für neoom AI.

Diese Datei definiert Entitäten zur Text-Eingabe, mit denen Einstellungen am lokalen
BEAAM Gateway vorgenommen werden können, deren Wert eine Kennung ist
(z. B. das am Ladepunkt ausgewählte Fahrzeug, EV_SELECTED).
"""

from collections.abc import Callable
from typing import Any

from homeassistant.components.text import TextEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, LOGGER, SettingSpec
from .coordinator import NeoomConfigEntry, NeoomLocalCoordinator
from .helpers import classify_setting, get_friendly_thing_name


async def async_setup_entry(
    hass: HomeAssistant,
    entry: NeoomConfigEntry,
    async_add_entities: Callable[[list[TextEntity]], None],
) -> None:
    """Richtet die Text-Plattform basierend auf dem Konfigurationseintrag ein.

    Erstellt Text-Entitäten für alle erkannten Text-Einstellungen der Things
    und überwacht spätere Coordinator-Updates für neu erkannte Entitäten.
    """
    local_coordinator = entry.runtime_data.local

    known_text_ids: set[str] = set()

    @callback
    def _async_check_entities() -> None:
        """Prüft auf neu verfügbare Einstellungen und legt entsprechende Text-Entitäten an."""
        if not local_coordinator.data:
            return

        beaam_config = local_coordinator.data.get("config", {})
        settings_map = local_coordinator.data.get("settings", {})

        if not beaam_config or not settings_map:
            return

        things = beaam_config.get("things", {})
        if not isinstance(things, dict):
            return

        new_entities: list[TextEntity] = []

        for thing_id, thing_data in things.items():
            if not thing_data or not isinstance(thing_data, dict):
                continue

            thing_settings = settings_map.get(thing_id)
            if not thing_settings or not isinstance(thing_settings, dict):
                continue

            for key, val in thing_settings.items():
                spec, _known = classify_setting(key, val)
                if spec is None or spec.platform != "text":
                    continue

                unique_id = f"{thing_id}_{key}_text"
                if unique_id not in known_text_ids:
                    known_text_ids.add(unique_id)
                    new_entities.append(
                        NeoomSettingText(
                            coordinator=local_coordinator,
                            thing_id=thing_id,
                            thing_data=thing_data,
                            setting_key=key,
                            spec=spec,
                        )
                    )

        if new_entities:
            async_add_entities(new_entities)

    _async_check_entities()
    entry.async_on_unload(
        local_coordinator.async_add_listener(_async_check_entities)
    )


class NeoomSettingText(CoordinatorEntity, TextEntity):
    """Repräsentation einer Einstellung, deren Wert ein Text ist (Text Entity)."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: NeoomLocalCoordinator,
        thing_id: str,
        thing_data: dict[str, Any],
        setting_key: str,
        spec: SettingSpec,
    ) -> None:
        """Initialisiert die Text-Entität."""
        super().__init__(coordinator)
        self._thing_id = thing_id
        self._thing_type: str = thing_data.get("type", "Unknown")
        self._setting_key = setting_key

        beaam_config = coordinator.data.get("config", {}) if coordinator.data else {}
        self._friendly_thing_name = get_friendly_thing_name(beaam_config, thing_id, self._thing_type)

        self._attr_name = spec.name or setting_key.replace("_", " ").title()
        self._attr_translation_key = setting_key.lower()
        self._attr_unique_id = f"{thing_id}_{setting_key}_text"
        self._attr_icon = "mdi:car-electric" if setting_key == "EV_SELECTED" else "mdi:form-textbox"

    @property
    def native_value(self) -> str | None:
        """Gibt den aktuell im Gateway gesetzten Wert zurück."""
        if not self.coordinator.data:
            return None

        settings_map = self.coordinator.data.get("settings", {})
        val = settings_map.get(self._thing_id, {}).get(self._setting_key)
        return None if val is None else str(val)

    async def async_set_value(self, value: str) -> None:
        """Wird aufgerufen, wenn der Benutzer einen neuen Text eingibt."""
        LOGGER.info("Setze Text-Einstellung %s am Gerät %s auf %s", self._setting_key, self._thing_id, value)
        await self.coordinator.async_send_setting(self._thing_id, self._setting_key, value)

    @property
    def device_info(self) -> DeviceInfo:
        """Verknüpfung der Entität mit dem physischen Gerät (Thing) im Device Registry."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._thing_id)},
            name=f"neoom {getattr(self, '_friendly_thing_name', self._thing_type)}",
            manufacturer="neoom",
            model=self._thing_type,
            **self.coordinator.gateway_link,
        )
