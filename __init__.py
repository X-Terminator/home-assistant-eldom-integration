"""The MyEldom integration."""
from datetime import timedelta
import logging

from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .MyEldom import MyEldom
from .const import DOMAIN, ELDOM_DEBUG

_LOGGER = logging.getLogger(__name__)
_LOGGER.setLevel(logging.DEBUG)

PLATFORMS = ["climate", "sensor"]


class MyEldomUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching MyEldom data."""

    def __init__(
        self,
        hass: HomeAssistant,
        *,
        myeldom_data_connection: MyEldom,
    ) -> None:
        """Initialize global MyEldom data updater."""
        self.myeldom_data_connection = myeldom_data_connection

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_method=myeldom_data_connection.fetch_all_heaters,
            update_interval=timedelta(seconds=30),
        )


async def async_setup_entry(hass, entry):
    """Set up the MyEldom heater."""
    myeldom_data_connection = MyEldom(
        entry.data[CONF_USERNAME], entry.data[CONF_PASSWORD], debug=ELDOM_DEBUG
    )
    if not await myeldom_data_connection.connect(
        websession=async_get_clientsession(hass)
    ):
        raise ConfigEntryNotReady

    hass.data[DOMAIN] = MyEldomUpdateCoordinator(
        hass,
        myeldom_data_connection=myeldom_data_connection,
    )

    await hass.data[DOMAIN].async_config_entry_first_refresh()

    hass.config_entries.async_setup_platforms(entry, PLATFORMS)
    return True


async def async_unload_entry(hass, entry):
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
