"""Valetudo Control integration for Home Assistant."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig

from .const import DOMAIN
from .coordinator import ValetudoControlCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.BUTTON, Platform.SENSOR, Platform.SWITCH]

async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Valetudo Control component."""
    # For HACS installations, the frontend card is automatically registered
    # For manual installations, we need to register the card
    try:
        # Try to register the card for manual installations
        import os
        hass_config_dir = hass.config.path()
        manual_card_path = os.path.join(hass_config_dir, "www", "valetudo-control-card.js")
        if os.path.exists(manual_card_path):
            await hass.http.async_register_static_paths([
                StaticPathConfig(
                    "/valetudo-control-card.js",
                    manual_card_path,
                    False
                )
            ])
            add_extra_js_url(hass, "/valetudo-control-card.js")
        # If the file doesn't exist, assume HACS installation and do nothing
        # HACS will handle the frontend resource registration
    except Exception as e:
        _LOGGER.debug("Could not register frontend card: %s", e)
    
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Valetudo Control from a config entry."""
    coordinator = ValetudoControlCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    
    # Forward the setup to the platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    # Register services
    async def handle_send_command(call):
        """Handle the send_command service call."""
        velocity = call.data.get("velocity")
        angle = call.data.get("angle")
        # Get the coordinator for the config entry
        coordinator = hass.data[DOMAIN][entry.entry_id]
        await coordinator.async_send_command(velocity, angle)
    
    async def handle_dock(call):
        """Handle the dock service call."""
        # Get the coordinator for the config entry
        coordinator = hass.data[DOMAIN][entry.entry_id]
        await coordinator.async_dock()
    
    async def handle_play_sound(call):
        """Handle the play_sound service call."""
        # Get the coordinator for the config entry
        coordinator = hass.data[DOMAIN][entry.entry_id]
        await coordinator.async_play_sound()
    
    async def handle_set_manual_control_state(call):
        """Handle the set_manual_control_state service call."""
        enable = call.data.get("enable")
        # Get the coordinator for the config entry
        coordinator = hass.data[DOMAIN][entry.entry_id]
        await coordinator.async_set_manual_control_state(enable)
    
    async def handle_get_water_usage_preset(call):
        """Handle the get_water_usage_preset service call."""
        # Get the coordinator for the config entry
        coordinator = hass.data[DOMAIN][entry.entry_id]
        preset = await coordinator.async_get_water_usage_preset()
        # Set the result in the call object
        call.set_result({"preset": preset or "off"})
    
    async def handle_set_water_usage_preset(call):
        """Handle the set_water_usage_preset service call."""
        preset = call.data.get("preset")
        # Get the coordinator for the config entry
        coordinator = hass.data[DOMAIN][entry.entry_id]
        await coordinator.async_set_water_usage_preset(preset)
    
    # Register domain services
    hass.services.async_register(DOMAIN, "send_command", handle_send_command)
    hass.services.async_register(DOMAIN, "dock", handle_dock)
    hass.services.async_register(DOMAIN, "play_sound", handle_play_sound)
    hass.services.async_register(DOMAIN, "set_manual_control_state", handle_set_manual_control_state)
    hass.services.async_register(DOMAIN, "get_water_usage_preset", handle_get_water_usage_preset, supports_response=True)
    hass.services.async_register(DOMAIN, "set_water_usage_preset", handle_set_water_usage_preset)
    
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
        # Unregister services
        hass.services.async_remove(DOMAIN, "send_command")
        hass.services.async_remove(DOMAIN, "dock")
        hass.services.async_remove(DOMAIN, "play_sound")
        hass.services.async_remove(DOMAIN, "set_manual_control_state")
        hass.services.async_remove(DOMAIN, "get_water_usage_preset")
        hass.services.async_remove(DOMAIN, "set_water_usage_preset")
    
    return unload_ok
