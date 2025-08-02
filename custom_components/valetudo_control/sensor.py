"""Sensor platform for Valetudo Control integration."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import ValetudoControlCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Valetudo Control sensors."""
    coordinator: ValetudoControlCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        ValetudoBatterySensor(coordinator)
    ])


class ValetudoBatterySensor(CoordinatorEntity, SensorEntity):
    """Representation of a Valetudo battery sensor."""

    def __init__(self, coordinator: ValetudoControlCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_name = f"{coordinator.api_name} Battery"
        self._attr_unique_id = f"{coordinator.api_unique_id}_battery"
        self._attr_device_class = SensorDeviceClass.BATTERY
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = "%"
        self._attr_device_info = coordinator.device_info

    @property
    def native_value(self) -> int | None:
        """Return the state of the sensor."""
        return self.coordinator.battery_level
    
