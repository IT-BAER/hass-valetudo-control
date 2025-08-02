"""Constants for the Valetudo Control integration."""
from homeassistant.const import Platform

DOMAIN = "valetudo_control"
PLATFORMS = [Platform.BUTTON, Platform.SENSOR, Platform.SWITCH]

CONF_VALETUDO_URL = "valetudo_url"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_DEBUG_MODE = "debug_mode"

DEFAULT_SPEED_LEVELS = [0.1, 0.6, 1.0]
DEFAULT_DEADZONE = 0.15
DEFAULT_ANGLE_EPSILON = 3.0  # Match reference implementation
DEFAULT_VELOCITY_EPSILON = 0.02  # Match reference implementation
DEFAULT_SEND_INTERVAL_MS = 100  # Match reference implementation
