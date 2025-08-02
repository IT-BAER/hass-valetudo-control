"""Config flow for Valetudo Control integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
import aiohttp
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import CONF_VALETUDO_URL, CONF_USERNAME, CONF_PASSWORD, CONF_DEBUG_MODE, DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_VALETUDO_URL): str,
        vol.Optional(CONF_USERNAME): str,
        vol.Optional(CONF_PASSWORD): str,
        vol.Optional(CONF_DEBUG_MODE, default=False): bool,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect."""
    session = async_get_clientsession(hass)
    
    url = data[CONF_VALETUDO_URL]
    username = data.get(CONF_USERNAME)
    password = data.get(CONF_PASSWORD)
    debug_mode = data.get(CONF_DEBUG_MODE, False)
    
    # Add http:// prefix if missing
    if not url.startswith(("http://", "https://")):
        url = f"http://{url}"
    
    # Check if URL ends with / and remove it if it does
    if url.endswith("/"):
        url = url[:-1]
    
    # Test connection to Valetudo API
    try:
        headers = {}
        if username and password:
            import base64
            auth_string = f"{username}:{password}"
            auth_bytes = auth_string.encode("utf-8")
            encoded_auth = base64.b64encode(auth_bytes).decode("utf-8")
            headers["Authorization"] = f"Basic {encoded_auth}"
        
        # Only log debug messages if debug mode is enabled
        if debug_mode:
            _LOGGER.debug("Attempting to connect to Valetudo at %s", url)
        # First, try a simple connection to see if the robot is reachable
        async with session.get(f"{url}/", headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as simple_response:
            if debug_mode:
                _LOGGER.debug("Simple connection test to %s/ returned status %s", url, simple_response.status)
        
        async with session.get(f"{url}/api/v2/robot/state", headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as response:
            if debug_mode:
                _LOGGER.debug("Received response with status code %s", response.status)
            if response.status == 401:
                raise InvalidAuth
            if response.status != 200:
                _LOGGER.error("Error connecting to Valetudo: Status code %s", response.status)
                raise CannotConnect
            
            # Try to get text content for debugging
            try:
                text_content = await response.text()
                if debug_mode:
                    _LOGGER.debug("Response content (first 200 chars): %s", text_content[:200] if text_content else "Empty response")
            except Exception as text_exc:
                if debug_mode:
                    _LOGGER.debug("Could not read response text: %s", text_exc)
        
        data = await response.json()
        # Get robot name from the state response
        robot_name = "Valetudo Robot"
        for attr in data.get("attributes", []):
            if attr.get("__class") == "RobotInformationAttribute":
                robot_name = attr.get("manufacturer", "Valetudo") + " " + attr.get("model", "Robot")
                break
                
    except aiohttp.ClientConnectorError as exc:
        _LOGGER.error("Error connecting to Valetudo: Cannot connect to %s - %s", url, exc)
        raise CannotConnect from exc
    except aiohttp.ClientError as exc:
        _LOGGER.error("Error connecting to Valetudo: %s", exc)
        # Check if this is a "Connection closed" error
        if "Connection closed" in str(exc):
            _LOGGER.error("Connection to Valetudo robot at %s was closed. Please check that the robot is powered on and running Valetudo.", url)
        raise CannotConnect from exc
    except Exception as exc:
        _LOGGER.error("Unexpected error connecting to Valetudo: %s", exc)
        raise CannotConnect from exc

    return {"title": robot_name}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Valetudo Control."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA
            )

        errors = {}

        try:
            info = await validate_input(self.hass, user_input)
        except CannotConnect:
            errors["base"] = "cannot_connect"
        except InvalidAuth:
            errors["base"] = "invalid_auth"
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception")
            errors["base"] = "unknown"
        else:
            # Ensure the URL is stored with the http:// prefix
            if not user_input[CONF_VALETUDO_URL].startswith(("http://", "https://")):
                user_input[CONF_VALETUDO_URL] = f"http://{user_input[CONF_VALETUDO_URL]}"
            return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
