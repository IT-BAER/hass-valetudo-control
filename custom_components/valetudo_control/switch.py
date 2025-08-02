"""Switch platform for Valetudo Control integration."""
from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
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
    """Set up the Valetudo Control switches."""
    coordinator: ValetudoControlCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([ValetudoManualControlSwitch(coordinator)])


class ValetudoManualControlSwitch(CoordinatorEntity, SwitchEntity):
    """Representation of a Valetudo manual control switch."""

    def __init__(self, coordinator: ValetudoControlCoordinator) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self._attr_name = f"{coordinator.api_name} Manual Control"
        self._attr_unique_id = f"{coordinator.api_unique_id}_manual_control"
        self._attr_icon = "mdi:gamepad-variant"
        self._attr_device_info = coordinator.device_info

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the switch on."""
        success = await self.coordinator.async_set_manual_control_state(True)
        if success:
            self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the switch off."""
        success = await self.coordinator.async_set_manual_control_state(False)
        if success:
            self.async_write_ha_state()

    @property
    def is_on(self) -> bool:
        """Return true if the switch is on."""
        return self.coordinator.manual_control_state or False
