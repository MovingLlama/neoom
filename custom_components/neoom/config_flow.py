"""Konfigurationsfluss (Config Flow) für die neoom AI Integration.

Diese Datei steuert den Einrichtungsassistenten, der dem Benutzer in der
Home Assistant Oberfläche angezeigt wird, wenn er die Integration hinzufügt.
"""

from typing import Any, Dict, Optional

import voluptuous as vol

import aiohttp

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
        """Initialisierung des Config Flows."""
        self.user_data: Dict[str, Any] = {}
        self.sites_dict: Dict[str, str] = {}

    async def async_step_user(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Behandelt den ersten Schritt der Einrichtung (Benutzereingabe).
        
        Wenn `user_input` None ist, wird das leere Formular angezeigt.
        Wenn `user_input` Daten enthält, werden diese verarbeitet und
        der Konfigurationseintrag erstellt.
        
        Args:
            user_input: Die vom Benutzer im Formular eingegebenen Daten.
            
        Returns:
            Ein FlowResult, das entweder das Formular anzeigt oder den Eintrag erstellt.
        """
        errors: Dict[str, str] = {}

        if user_input is not None:
            self.user_data = user_input
            
            # Cloud API aufrufen, um Sites zu laden
            token = user_input[CONF_CLOUD_TOKEN]
            url = f"{CLOUD_API_URL}/sites"
            headers = {"Authorization": f"Bearer {token}"}
            
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, headers=headers) as resp:
                        if resp.status == 401:
                            errors["base"] = "invalid_auth"
                        else:
                            resp.raise_for_status()
                            data = await resp.json()
                            
                            if isinstance(data, dict):
                                sites_list = data.get("items") or data.get("data") or data.get("sites", [])
                            else:
                                sites_list = data
                                
                            self.sites_dict = {}
                            if isinstance(sites_list, list):
                                for site in sites_list:
                                    if isinstance(site, dict):
                                        site_id = site.get("id") or site.get("siteId")
                                        site_name = site.get("name") or site.get("siteName", site_id)
                                        if site_id:
                                            self.sites_dict[str(site_id)] = str(site_name)
                            
                            if not self.sites_dict:
                                errors["base"] = "cannot_connect"
                                LOGGER.error("Keine Sites in der API-Antwort gefunden oder falsches Format.")
                            else:
                                # Gehe zum nächsten Schritt
                                return await self.async_step_site_selection()
            except Exception as e:
                LOGGER.exception("Unerwarteter Fehler beim Abrufen der Sites im Config Flow: %s", e)
                errors["base"] = "cannot_connect"

        # Schema für das Eingabeformular in der UI definieren.
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

    async def async_step_site_selection(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Zweiter Schritt: Auswahl des Standorts (Site)."""
        errors: Dict[str, str] = {}

        if user_input is not None:
            # Füge die ausgewählte Site ID zu den gesammelten Daten hinzu
            self.user_data[CONF_SITE_ID] = user_input[CONF_SITE_ID]
            
            site_name = self.sites_dict.get(user_input[CONF_SITE_ID], "neoom System")
            
            return self.async_create_entry(
                title=site_name, 
                data=self.user_data
            )

        data_schema = vol.Schema(
            {
                vol.Required(CONF_SITE_ID): vol.In(self.sites_dict)
            }
        )

        return self.async_show_form(
            step_id="site_selection",
            data_schema=data_schema,
            errors=errors
        )
