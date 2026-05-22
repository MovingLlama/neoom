"""Konfigurationsfluss (Config Flow) für die neoom AI Integration.

Diese Datei steuert den Einrichtungsassistenten, der dem Benutzer in der
Home Assistant Oberfläche angezeigt wird, wenn er die Integration hinzufügt.
"""

from typing import Any, Dict, List, Optional
import async_timeout
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

from .const import (
    DOMAIN,
    CONF_SITE_ID,
    CONF_CLOUD_TOKEN,
    CONF_BEAAM_IP,
    CONF_BEAAM_KEY,
    CLOUD_API_URL,
    LOGGER,
)


class NeoomConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Behandelt den Konfigurationsfluss für neoom AI.
    
    Diese Klasse erbt von ConfigFlow und definiert die Schritte, die der User
    durchlaufen muss, um die Integration zu konfigurieren.
    """

    # Version des Konfigurationsschemas. Nützlich für zukünftige Migrationen.
    VERSION = 1

    def __init__(self) -> None:
        """Initialisiert den Config Flow."""
        self.init_data: Dict[str, Any] = {}
        self.sites_list: Dict[str, str] = {}

    async def async_step_user(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Behandelt den ersten Schritt der Einrichtung (Benutzereingabe).
        
        Wenn `user_input` None ist, wird das leere Formular angezeigt.
        Wenn `user_input` Daten enthält, werden diese verarbeitet.
        Wir rufen die Liste der Standorte (Sites) aus der neoom Cloud ab, 
        um die passende Site ID automatisch auszuwählen oder als Dropdown anzubieten.
        
        Args:
            user_input: Die vom Benutzer im Formular eingegebenen Daten.
            
        Returns:
            Ein FlowResult, das entweder das Formular, Fehler oder den nächsten Schritt anzeigt.
        """
        errors: Dict[str, str] = {}

        if user_input is not None:
            self.init_data = user_input
            
            # Versuche, die Standorte (Sites) über das angegebene Cloud-Token abzurufen
            try:
                sites = await self._async_get_sites(user_input[CONF_CLOUD_TOKEN])
                if not sites:
                    LOGGER.warning("Keine Sites in der neoom AI Cloud für das angegebene Token gefunden.")
                    errors["base"] = "no_sites_found"
                else:
                    # Mappe die Site IDs zu lesbaren Namen (Name + Stadt)
                    self.sites_list = {
                        site["id"]: f"{site.get('name', 'Unbenannt')} ({site.get('city', 'Unbekannt')})"
                        for site in sites
                    }
                    
                    if len(sites) == 1:
                        # Nur ein Standort vorhanden: Automatisch auswählen und Setup abschließen
                        site_id = list(self.sites_list.keys())[0]
                        self.init_data[CONF_SITE_ID] = site_id
                        LOGGER.info("Genau eine Site gefunden (%s). Wähle diese automatisch aus.", self.sites_list[site_id])
                        return self.async_create_entry(
                            title=self.sites_list[site_id],
                            data=self.init_data
                        )
                    
                    # Mehrere Standorte vorhanden: Zeige den Auswahlschritt
                    LOGGER.info("%d Sites gefunden. Gehe zum Auswahlschritt.", len(sites))
                    return await self.async_step_select_site()
            except Exception as e:
                LOGGER.exception("Fehler beim Verbindungsaufbau zur neoom AI Cloud: %s", e)
                errors["base"] = "cannot_connect_cloud"

        # Schema für den ersten Schritt (ohne Site ID, da diese automatisch ermittelt wird)
        data_schema = vol.Schema(
            {
                vol.Required(CONF_CLOUD_TOKEN): str,  # neoom AI Bearer Token
                vol.Required(CONF_BEAAM_IP): str,     # IP-Adresse des lokalen Gateways
                vol.Required(CONF_BEAAM_KEY): str,    # API Key für lokales Gateway
            }
        )

        # Zeigt das Formular mit dem definierten Schema und eventuellen Fehlern an.
        return self.async_show_form(
            step_id="user", 
            data_schema=data_schema, 
            errors=errors
        )

    async def async_step_select_site(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Behandelt den Auswahlschritt für Standorte (Sites), falls mehrere existieren.
        
        Args:
            user_input: Der vom Benutzer ausgewählte Standort.
            
        Returns:
            Ein FlowResult zur Erstellung des Eintrags oder Anzeige des Formulars.
        """
        errors: Dict[str, str] = {}

        if user_input is not None:
            site_id = user_input[CONF_SITE_ID]
            self.init_data[CONF_SITE_ID] = site_id
            title = self.sites_list.get(site_id, "neoom System")
            
            LOGGER.info("Benutzer hat Site ausgewählt: %s (%s)", title, site_id)
            return self.async_create_entry(
                title=title,
                data=self.init_data
            )

        # Dropdown Schema zur Auswahl der Site
        data_schema = vol.Schema(
            {
                vol.Required(
                    CONF_SITE_ID,
                    default=list(self.sites_list.keys())[0] if self.sites_list else None
                ): vol.In(self.sites_list)
            }
        )

        return self.async_show_form(
            step_id="select_site",
            data_schema=data_schema,
            errors=errors
        )

    async def _async_get_sites(self, token: str) -> List[Dict[str, Any]]:
        """Hilfsfunktion: Ruft die Liste aller verfügbaren Standorte aus der neoom AI Cloud ab.
        
        Args:
            token: Das Authentifizierungs-Token (Bearer Token).
            
        Returns:
            Eine Liste von Dictionaries, welche die Site-Informationen enthalten.
        """
        url = f"{CLOUD_API_URL}/sites/"
        headers = {"Authorization": f"Bearer {token}"}
        
        # Nutzen der Home Assistant asynchronen HTTP Client Session
        session = self.hass.helpers.aiohttp_client.async_get_clientsession()
        
        async with async_timeout.timeout(10):
            async with session.get(url, headers=headers) as resp:
                resp.raise_for_status()
                data = await resp.json()
                return data.get("sites", [])

