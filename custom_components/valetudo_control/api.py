"""API for Valetudo Control integration."""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, Optional
import aiohttp
import base64
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.core import HomeAssistant

from .const import (
    CONF_VALETUDO_URL,
    CONF_USERNAME,
    CONF_PASSWORD,
    CONF_DEBUG_MODE,
    DEFAULT_SPEED_LEVELS,
    DEFAULT_DEADZONE,
    DEFAULT_ANGLE_EPSILON,
    DEFAULT_VELOCITY_EPSILON,
    DEFAULT_SEND_INTERVAL_MS
)

_LOGGER = logging.getLogger(__name__)


class ValetudoControlAPI:
    """Class to communicate with the Valetudo robot."""

    def __init__(self, hass: HomeAssistant, entry_data: Dict[str, Any]) -> None:
        """Initialize the API."""
        self.hass = hass
        self.session = async_get_clientsession(hass)
        url = entry_data[CONF_VALETUDO_URL]
        # Add http:// prefix if missing
        if not url.startswith(("http://", "https://")):
            url = f"http://{url}"
        self.url = url.rstrip("/")
        self.username = entry_data.get(CONF_USERNAME)
        self.password = entry_data.get(CONF_PASSWORD)
        self.debug_mode = entry_data.get(CONF_DEBUG_MODE, False)
        
        # Control parameters
        self.speed_levels = DEFAULT_SPEED_LEVELS
        self.deadzone = DEFAULT_DEADZONE
        self.angle_epsilon = DEFAULT_ANGLE_EPSILON
        self.velocity_epsilon = DEFAULT_VELOCITY_EPSILON
        self.send_interval_ms = DEFAULT_SEND_INTERVAL_MS
        self.speed_index = 1  # Default to medium speed
        
        # Last sent values for change detection
        self.last_sent = {"angle": None, "velocity": None}
        self.last_send_time = 0
        self.manual_control_enabled = False
    
    def _is_debug_mode(self) -> bool:
        """Check if debug mode is enabled."""
        return self.debug_mode
    
    def _debug(self, msg: str, *args) -> None:
        """Log debug message if debug mode is enabled."""
        if self._is_debug_mode():
            _LOGGER.debug(msg, *args)

    def _get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers if credentials are provided."""
        headers = {}
        if self.username and self.password:
            auth_string = f"{self.username}:{self.password}"
            auth_bytes = auth_string.encode("utf-8")
            encoded_auth = base64.b64encode(auth_bytes).decode("utf-8")
            headers["Authorization"] = f"Basic {encoded_auth}"
        return headers

    async def get_robot_state(self) -> Optional[Dict[str, Any]]:
        """Get the current state of the robot."""
        try:
            headers = self._get_auth_headers()
            self._debug("Attempting to get robot state from %s", self.url)
            async with self.session.get(
                f"{self.url}/api/v2/robot/state",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                self._debug("Received robot state response with status code %s", response.status)
                if response.status == 200:
                    # Try to get text content for debugging
                    try:
                        text_content = await response.text()
                        self._debug("Robot state response content (first 200 chars): %s", text_content[:200] if text_content else "Empty response")
                    except Exception as text_exc:
                        self._debug("Could not read robot state response text: %s", text_exc)
                    return await response.json()
                else:
                    _LOGGER.warning("Error getting robot state: Status code %s", response.status)
        except aiohttp.ClientConnectorError as exc:
            _LOGGER.error("Error connecting to Valetudo: Cannot connect to %s - %s", self.url, exc)
        except aiohttp.ClientError as exc:
            _LOGGER.error("Error getting robot state: %s", exc)
            # Check if this is a "Connection closed" error
            if "Connection closed" in str(exc):
                _LOGGER.error("Connection to Valetudo robot at %s was closed. Please check that the robot is powered on and running Valetudo.", self.url)
        except Exception as exc:
            _LOGGER.error("Unexpected error getting robot state: %s", exc)
        return None

    async def get_battery_level(self) -> Optional[int]:
        """Get the battery level of the robot."""
        state = await self.get_robot_state()
        if state:
            for attr in state.get("attributes", []):
                if attr.get("__class") == "BatteryStateAttribute":
                    return attr.get("level")
        return None

    async def send_command(self, velocity: float, angle: float) -> bool:
        """Send a movement command to the robot."""
        import time
        
        # Round values for comparison
        angle = round(angle, 1)
        velocity = max(-1.0, min(1.0, velocity))  # Clamp to [-1, 1]
        velocity = round(velocity, 3)
        
        payload = {
            "action": "move",
            "vector": {"velocity": velocity, "angle": angle}
        }
        
        try:
            headers = self._get_auth_headers()
            self._debug("Sending command to %s with velocity=%s, angle=%s", self.url, velocity, angle)
            async with self.session.put(
                f"{self.url}/api/v2/robot/capabilities/HighResolutionManualControlCapability",
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                self._debug("Received command response with status code %s", response.status)
                if response.status == 200:
                    self.last_sent = {"angle": angle, "velocity": velocity}
                    # Update last send time
                    self.last_send_time = int(time.time() * 1000)
                    return True
                else:
                    _LOGGER.warning("Failed to send command. Status: %s", response.status)
                    # Try to read the response body for more information
                    try:
                        response_text = await response.text()
                        self._debug("Response body: %s", response_text)
                    except Exception as e:
                        self._debug("Could not read response body: %s", e)
        except aiohttp.ClientConnectorError as exc:
            _LOGGER.error("Error connecting to Valetudo: Cannot connect to %s - %s", self.url, exc)
        except aiohttp.ClientError as exc:
            _LOGGER.error("Error sending command: %s", exc)
            # Check if this is a "Connection closed" error
            if "Connection closed" in str(exc) or "Connection reset" in str(exc):
                _LOGGER.warning("Connection to Valetudo robot at %s was reset. This may be normal if sending commands too frequently.", self.url)
        except Exception as exc:
            _LOGGER.error("Unexpected error sending command: %s", exc)
        
        return False

    async def get_manual_control_state(self) -> Optional[bool]:
        """Get the manual control state of the robot."""
        try:
            headers = self._get_auth_headers()
            self._debug("Attempting to get manual control state from %s", self.url)
            async with self.session.get(
                f"{self.url}/api/v2/robot/capabilities/HighResolutionManualControlCapability",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                self._debug("Received manual control state response with status code %s", response.status)
                if response.status == 200:
                    data = await response.json()
                    enabled = data.get("enabled", False)
                    self._debug("Manual control state: %s", enabled)
                    return enabled
                else:
                    _LOGGER.warning("Error getting manual control state: Status code %s", response.status)
                    # Try to read the response body for more information
                    try:
                        response_text = await response.text()
                        self._debug("Response body: %s", response_text)
                    except Exception as e:
                        self._debug("Could not read response body: %s", e)
        except aiohttp.ClientConnectorError as exc:
            _LOGGER.error("Error connecting to Valetudo: Cannot connect to %s - %s", self.url, exc)
        except aiohttp.ClientError as exc:
            _LOGGER.error("Error getting manual control state: %s", exc)
        except Exception as exc:
            _LOGGER.exception("Unexpected error getting manual control state")
        return None

    async def set_manual_control_state(self, enable: bool) -> bool:
        """Enable or disable manual control on the robot."""
        payload = {
            "action": "enable" if enable else "disable"
        }
        
        try:
            headers = self._get_auth_headers()
            self._debug("Setting manual control state to %s on %s", enable, self.url)
            async with self.session.put(
                f"{self.url}/api/v2/robot/capabilities/HighResolutionManualControlCapability",
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                self._debug("Received manual control state response with status code %s", response.status)
                if response.status == 200:
                    self._debug("Successfully set manual control state to %s", enable)
                    # Update local state
                    self.manual_control_enabled = enable
                    return True
                else:
                    _LOGGER.warning("Failed to set manual control state. Status: %s", response.status)
                    # Try to read the response body for more information
                    try:
                        response_text = await response.text()
                        self._debug("Response body: %s", response_text)
                    except Exception as e:
                        self._debug("Could not read response body: %s", e)
        except aiohttp.ClientConnectorError as exc:
            _LOGGER.error("Error connecting to Valetudo: Cannot connect to %s - %s", self.url, exc)
        except aiohttp.ClientError as exc:
            _LOGGER.error("Error setting manual control state: %s", exc)
        except Exception as exc:
            _LOGGER.exception("Unexpected error setting manual control state")
        
        return False

    async def play_sound(self) -> bool:
        """Play a locate sound on the robot."""
        try:
            headers = self._get_auth_headers()
            self._debug("Sending play locate sound command to %s", self.url)
            payload = {"action": "locate"}
            async with self.session.put(
                f"{self.url}/api/v2/robot/capabilities/LocateCapability",
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                self._debug("Received play locate sound response with status code %s", response.status)
                return response.status == 200
        except aiohttp.ClientConnectorError as exc:
            _LOGGER.error("Error connecting to Valetudo: Cannot connect to %s - %s", self.url, exc)
            return False
        except aiohttp.ClientError as exc:
            _LOGGER.error("Error playing locate sound: %s", exc)
            # Check if this is a "Connection closed" error
            if "Connection closed" in str(exc):
                _LOGGER.error("Connection to Valetudo robot at %s was closed. Please check that the robot is powered on and running Valetudo.", self.url)
            return False
        except Exception as exc:
            _LOGGER.error("Unexpected error playing locate sound: %s", exc)
            return False

    async def dock(self) -> bool:
        """Send the robot to its dock."""
        try:
            headers = self._get_auth_headers()
            self._debug("Sending dock command to %s", self.url)
            payload = {"action": "home"}
            async with self.session.put(
                f"{self.url}/api/v2/robot/capabilities/BasicControlCapability",
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                self._debug("Received dock response with status code %s", response.status)
                return response.status == 200
        except aiohttp.ClientConnectorError as exc:
            _LOGGER.error("Error connecting to Valetudo: Cannot connect to %s - %s", self.url, exc)
            return False
        except aiohttp.ClientError as exc:
            _LOGGER.error("Error docking robot: %s", exc)
            # Check if this is a "Connection closed" error
            if "Connection closed" in str(exc):
                _LOGGER.error("Connection to Valetudo robot at %s was closed. Please check that the robot is powered on and running Valetudo.", self.url)
            return False
        except Exception as exc:
            _LOGGER.error("Unexpected error docking robot: %s", exc)
            return False
      
    async def get_water_usage_preset(self) -> Optional[str]:
        """Get the current water usage preset of the robot."""
        try:
            headers = self._get_auth_headers()
            self._debug("Attempting to get water usage preset from %s", self.url)
            async with self.session.get(
                f"{self.url}/api/v2/robot/capabilities/WaterUsageControlCapability",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                self._debug("Received water usage preset response with status code %s", response.status)
                if response.status == 200:
                    data = await response.json()
                    preset = data.get("currentPreset", {}).get("name", "off")
                    self._debug("Water usage preset: %s", preset)
                    return preset
                else:
                    _LOGGER.warning("Error getting water usage preset: Status code %s", response.status)
                    # Try to read the response body for more information
                    try:
                        response_text = await response.text()
                        self._debug("Response body: %s", response_text)
                    except Exception as e:
                        self._debug("Could not read response body: %s", e)
        except aiohttp.ClientConnectorError as exc:
            _LOGGER.error("Error connecting to Valetudo: Cannot connect to %s - %s", self.url, exc)
        except aiohttp.ClientError as exc:
            _LOGGER.error("Error getting water usage preset: %s", exc)
        except Exception as exc:
            _LOGGER.exception("Unexpected error getting water usage preset")
        return None

    async def set_water_usage_preset(self, preset: str) -> bool:
        """Set the water usage preset on the robot."""
        payload = {
            "name": preset
        }
        
        try:
            headers = self._get_auth_headers()
            self._debug("Setting water usage preset to %s on %s", preset, self.url)
            async with self.session.put(
                f"{self.url}/api/v2/robot/capabilities/WaterUsageControlCapability/preset",
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                self._debug("Received water usage preset response with status code %s", response.status)
                if response.status == 200:
                    self._debug("Successfully set water usage preset to %s", preset)
                    return True
                else:
                    _LOGGER.warning("Failed to set water usage preset. Status: %s", response.status)
                    # Try to read the response body for more information
                    try:
                        response_text = await response.text()
                        self._debug("Response body: %s", response_text)
                    except Exception as e:
                        self._debug("Could not read response body: %s", e)
        except aiohttp.ClientConnectorError as exc:
            _LOGGER.error("Error connecting to Valetudo: Cannot connect to %s - %s", self.url, exc)
        except aiohttp.ClientError as exc:
            _LOGGER.error("Error setting water usage preset: %s", exc)
        except Exception as exc:
            _LOGGER.exception("Unexpected error setting water usage preset")
        
        return False


    def get_current_speed(self) -> float:
        """Get the current speed level."""
        return self.speed_levels[self.speed_index]

    def calculate_movement(self, x_axis: float, y_axis: float) -> tuple[float, float]:
        """Calculate velocity and angle based on joystick position.
        
        Args:
            x_axis: Joystick X axis position (-1 to 1)
            y_axis: Joystick Y axis position (-1 to 1)
            
        Returns:
            tuple: (velocity, angle_deg)
        """
        abs_x, abs_y = abs(x_axis), abs(y_axis)
        max_speed = self.get_current_speed()
        
        # Deadzone - No movement
        if abs_x < self.deadzone and abs_y < self.deadzone:
            return 0.0, 0.0
        
        # Mostly vertical movement
        if abs_y > self.deadzone and abs_x < (self.deadzone * 1.5):
            velocity = self._normalize_axis_value(abs_y) * max_speed
            velocity = velocity if y_axis > 0 else -velocity
            return max(-1.0, min(1.0, velocity)), 0.0
        
        # Mostly horizontal movement - pure rotation
        if abs_x > self.deadzone and abs_y < (self.deadzone * 1.5):
            angle = 90 if x_axis > 0 else -90
            return 0.0, angle
        
        # Combined movement - both velocity and angle
        corrected_x = -x_axis if y_axis < 0 else x_axis
        import math
        angle_deg = math.degrees(math.atan2(corrected_x, y_axis))
        
        magnitude = math.sqrt(x_axis ** 2 + y_axis ** 2)
        velocity = self._normalize_axis_value(magnitude) * max_speed
        velocity = velocity if y_axis > 0 else -velocity
        
        return max(-1.0, min(1.0, velocity)), angle_deg

    def _normalize_axis_value(self, value: float) -> float:
        """Normalize joystick axis value accounting for deadzone."""
        return max(0.0, value - self.deadzone) / (1 - self.deadzone)
