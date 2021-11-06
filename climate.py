"""Support for Eldom wifi-enabled home heaters."""
import logging

from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    HVAC_MODE_HEAT,
    HVAC_MODE_OFF,
    SUPPORT_TARGET_TEMPERATURE,
)
from homeassistant.const import ATTR_TEMPERATURE, TEMP_CELSIUS
from homeassistant.core import callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .MyEldom import Heater
from .const import DOMAIN, ELDOM_DEBUG, MANUFACTURER, MAX_TEMP, MIN_TEMP

_LOGGER = logging.getLogger(__name__)
# _LOGGER.setLevel(logging.DEBUG)


SUPPORT_FLAGS = SUPPORT_TARGET_TEMPERATURE


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the Eldom climate."""
    myeldom_data_coordinator = hass.data[DOMAIN]

    if ELDOM_DEBUG:
        _LOGGER.debug(f"myeldom_data_coordinator.data: {myeldom_data_coordinator.data}")

    entities = [
        EldomHeater(myeldom_data_coordinator, eldom_device)
        for eldom_device in myeldom_data_coordinator.data.values()
        if isinstance(eldom_device, Heater)
    ]
    if ELDOM_DEBUG:
        _LOGGER.debug(f"Entities: {entities}")
    async_add_entities(entities)


class EldomHeater(CoordinatorEntity, ClimateEntity):
    """Representation of a Eldom Convection Heater device."""

    def __init__(self, coordinator, heater: Heater):
        """Initialize the heater thermostat."""
        super().__init__(coordinator)
        self._heater = heater
        self._icon = "mdi:radiator"
        self._available = False

        self._id = heater.real_device_id
        self._attr_unique_id = heater.real_device_id
        self._attr_name = heater.name

        model = "Unknown"
        if heater.hw_version == "14":
            model = "NHC-PC5"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, str(heater.real_device_id))},
            manufacturer=MANUFACTURER,
            model=model,
            name=self.name,
            sw_version=heater.sw_version,
        )
        self._update_attr(heater)

    @property
    def icon(self):
        """Return the icon."""
        return self._icon

    @property
    def supported_features(self):
        """Return the list of supported features."""
        return SUPPORT_FLAGS

    @property
    def available(self):
        """Return True if entity is available."""
        return super().available and self._available

    @property
    def unique_id(self):
        """Return a unique ID."""
        return self._heater.real_device_id

    @property
    def name(self):
        """Return the name of the entity."""
        return self._heater.name

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""

        attr = {
            "hw_version": self._heater.hw_version,
            "sw_ersion": self._heater.sw_version,
            "last_update": self._heater.last_updated,
            "id": self._heater.id,
            "device_id": self._heater.real_device_id,
            # "state": self._heater.state,
            # "power": self._heater.power,
            # "pcb_temp": self._heater.pcb_temp,
            # "open_window": self._heater.open_window,
            # "energy_day": self._heater.energy_day,
            # "energy_night": self._heater.energy_night,
            "energy_total": self._heater.energy_total,
            # "raw": json.loads(self._heater.raw_data),
        }
        return attr

    @property
    def temperature_unit(self):
        """Return the unit of measurement which this thermostat uses."""
        return TEMP_CELSIUS

    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        return self._heater.set_temp

    @property
    def target_temperature_step(self):
        """Return the supported step of target temperature."""
        return 0.5

    @property
    def current_temperature(self):
        """Return the current temperature."""
        return self._heater.current_temp

    @property
    def min_temp(self):
        """Return the minimum temperature."""
        return MIN_TEMP

    @property
    def max_temp(self):
        """Return the maximum temperature."""
        return MAX_TEMP

    @property
    def hvac_mode(self) -> str:
        """Return hvac operation ie. heat, cool mode.

        Need to be one of HVAC_MODE_*.
        """
        if self._heater.state == 1:
            return HVAC_MODE_HEAT
        return HVAC_MODE_OFF

    @property
    def hvac_modes(self):
        """Return the list of available hvac operation modes.

        Need to be a subset of HVAC_MODES.
        """
        return [HVAC_MODE_HEAT, HVAC_MODE_OFF]

    async def async_set_temperature(self, **kwargs):
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return
        await self.coordinator.myeldom_data_connection.set_temperature(
            self._heater, temperature
        )

    async def async_set_hvac_mode(self, hvac_mode):
        """Set new target hvac mode."""
        if hvac_mode == HVAC_MODE_HEAT:
            await self.coordinator.myeldom_data_connection.set_state(self._heater, 1)
        else:
            await self.coordinator.myeldom_data_connection.set_state(self._heater, 0)

    async def async_update(self):
        """Retrieve latest state."""
        if await self.coordinator.myeldom_data_connection.fetch_heater_data(
            self._heater
        ):
            _LOGGER.debug(f"updated device: {self._heater.name}")
        else:
            _LOGGER.error(f"error updating device: {self._heater.name}")

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._update_attr(self.coordinator.data[self._id])
        self.async_write_ha_state()

    @callback
    def _update_attr(self, heater):
        self._available = heater.available
