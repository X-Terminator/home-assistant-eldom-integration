"""Support for mill wifi-enabled home heaters."""
from __future__ import annotations

from homeassistant.components.sensor import (
    DEVICE_CLASS_ENERGY,
    STATE_CLASS_TOTAL_INCREASING,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.const import ENERGY_KILO_WATT_HOUR
from homeassistant.core import callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .MyEldom import Heater
from .const import CONSUMPTION_TOTAL, DOMAIN, MANUFACTURER

HEATER_SENSOR_TYPE = SensorEntityDescription(
    key=CONSUMPTION_TOTAL,
    device_class=DEVICE_CLASS_ENERGY,
    native_unit_of_measurement=ENERGY_KILO_WATT_HOUR,
    state_class=STATE_CLASS_TOTAL_INCREASING,
    name="Total Consumption",
)


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the Eldom heater sensor."""

    myeldom_data_coordinator = hass.data[DOMAIN]

    entities = [
        EldomSensor(
            myeldom_data_coordinator,
            HEATER_SENSOR_TYPE,
            eldom_device,
        )
        for eldom_device in myeldom_data_coordinator.data.values()
        if isinstance(eldom_device, Heater)
        # for entity_description in HEATER_SENSOR_TYPES
    ]

    async_add_entities(entities)


class EldomSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Eldom Sensor device."""

    def __init__(
        self,
        coordinator,
        entity_description: SensorEntityDescription,
        eldom_device: Heater,
    ):
        """Initialize the sensor."""
        super().__init__(coordinator)

        self._id = eldom_device.real_device_id
        self.entity_description = entity_description
        self._available = False

        self._attr_name = f"{eldom_device.name} {entity_description.name}"
        self._attr_unique_id = f"{eldom_device.real_device_id}_{entity_description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, str(eldom_device.real_device_id))},
            name=self.name,
            manufacturer=MANUFACTURER,
        )

        self._update_attr(eldom_device)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._update_attr(self.coordinator.data[self._id])
        self.async_write_ha_state()

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return super().available and self._available

    @callback
    def _update_attr(self, device):
        self._available = device.available
        self._attr_native_value = getattr(device, self.entity_description.key)
