"""Data update coordinator for Valetudo Control integration."""
from __future__ import annotations

import asyncio
from datetime import timedelta
import logging
from typing import Any, Optional

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import ValetudoControlAPI
from .const import DOMAIN, CONF_DEBUG_MODE

_LOGGER = logging.getLogger(__name__)

UPDATE_INTERVAL = timedelta(seconds=30)


class ValetudoControlCoordinator(DataUpdateCoordinator):
    """Class to manage fetching Valetudo data."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
        )
        self.entry = entry
        self.api = ValetudoControlAPI(hass, entry.data)
        self.battery_level: int | None = None
        self.manual_control_state: bool | None = None
        
        # Get device info from entry title or use default
        self.api_name = entry.title
        self.api_unique_id = entry.entry_id
    
    def _is_debug_mode(self) -> bool:
        """Check if debug mode is enabled."""
        return self.entry.data.get(CONF_DEBUG_MODE, False)
    
    def _debug(self, msg: str, *args) -> None:
        """Log debug message if debug mode is enabled."""
        if self._is_debug_mode():
            _LOGGER.debug(msg, *args)

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device information about this Valetudo device."""
        return {
            "identifiers": {(DOMAIN, self.api_unique_id)},
            "name": self.api_name,
            "manufacturer": "Valetudo",
            "model": "Robot Vacuum",
            "sw_version": "Unknown",
        }

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from Valetudo API."""
        try:
            battery_level = await self.api.get_battery_level()
            if battery_level is not None:
                self.battery_level = battery_level
            
            # Fetch manual control state
            manual_control_state = await self.api.get_manual_control_state()
            self._debug("Fetched manual control state: %s", manual_control_state)
            if manual_control_state is not None:
                self.manual_control_state = manual_control_state
            
            return {
                "battery_level": battery_level,
                "manual_control_state": manual_control_state,
            }
        except Exception as err:
            _LOGGER.error("Error communicating with API: %s", err)
            raise UpdateFailed(f"Error communicating with API: {err}") from err

    async def async_send_command(self, velocity: float, angle: float) -> bool:
        """Send a movement command to the robot."""
        return await self.api.send_command(velocity, angle)

    async def async_dock(self) -> bool:
        """Send the robot to its dock."""
        return await self.api.dock()

    async def async_play_sound(self) -> bool:
        """Play a test sound on the robot."""
        return await self.api.play_sound()

    async def async_set_manual_control_state(self, enable: bool) -> bool:
        """Enable or disable manual control on the robot."""
        success = await self.api.set_manual_control_state(enable)
        if success:
            # Update the local state
            self.manual_control_state = enable
            # Trigger an update to ensure consistency
            await self.async_request_refresh()
        return success
      
    async def async_get_water_usage_preset(self) -> Optional[str]:
        """Get the current water usage preset of the robot."""
        return await self.api.get_water_usage_preset()
    
    async def async_set_water_usage_preset(self, preset: str) -> bool:
        """Set the water usage preset on the robot."""
        return await self.api.set_water_usage_preset(preset)
    
