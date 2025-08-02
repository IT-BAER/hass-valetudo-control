"""Button platform for Valetudo Control integration."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import ValetudoControlCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Valetudo Control buttons."""
    coordinator: ValetudoControlCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        ValetudoDockButton(coordinator),
        ValetudoPlaySoundButton(coordinator),
    ])


class ValetudoDockButton(ButtonEntity):
    """Representation of a Valetudo dock button."""

    def __init__(self, coordinator: ValetudoControlCoordinator) -> None:
        """Initialize the button."""
        self.coordinator = coordinator
        self._attr_name = f"{coordinator.api_name} Dock"
        self._attr_unique_id = f"{coordinator.api_unique_id}_dock"
        self._attr_icon = "mdi:home-map-marker"
        self._attr_device_info = coordinator.device_info

    async def async_press(self) -> None:
        """Handle the button press."""
        await self.coordinator.api.dock()
        await self.coordinator.async_request_refresh()


class ValetudoPlaySoundButton(ButtonEntity):
    """Representation of a Valetudo play sound button."""

    def __init__(self, coordinator: ValetudoControlCoordinator) -> None:
        """Initialize the button."""
        self.coordinator = coordinator
        self._attr_name = f"{coordinator.api_name} Locate"
        self._attr_unique_id = f"{coordinator.api_unique_id}_play_sound"
        self._attr_icon = "mdi:map-marker"
        self._attr_device_info = coordinator.device_info

    async def async_press(self) -> None:
        """Handle the button press."""
        await self.coordinator.api.play_sound()


