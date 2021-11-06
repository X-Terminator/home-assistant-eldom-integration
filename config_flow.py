"""Adds config flow for Eldom integration."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .MyEldom import MyEldom
from .const import DOMAIN, ELDOM_DEBUG

USER_SCHEMA = vol.Schema(
    {vol.Required(CONF_USERNAME): str, vol.Required(CONF_PASSWORD): str}
)


class EldomConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Eldom integration."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self._async_show_setup_form()

        username = user_input[CONF_USERNAME].replace(" ", "")
        password = user_input[CONF_PASSWORD].replace(" ", "")

        eldom_data_connection = MyEldom(username, password, debug=ELDOM_DEBUG)

        errors = {}

        if not await eldom_data_connection.connect():
            errors["cannot_connect"] = "cannot_connect"
            return self._async_show_setup_form()

        await eldom_data_connection.disconnect()

        unique_id = username

        await self.async_set_unique_id(unique_id)
        self._abort_if_unique_id_configured()

        return self.async_create_entry(
            title=unique_id,
            data={CONF_USERNAME: username, CONF_PASSWORD: password},
        )

    @callback
    def _async_show_setup_form(
        self, errors: dict[str, str] | None = None
    ) -> FlowResult:
        """Show the setup form to the user."""
        return self.async_show_form(
            step_id="user",
            data_schema=USER_SCHEMA,
            errors=errors or {},
        )
