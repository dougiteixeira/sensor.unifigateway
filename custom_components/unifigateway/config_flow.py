"""Adds config flow (UI flow) for Unifi Gateway."""
import logging

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.helpers import config_validation as cv
from homeassistant.const import (
    CONF_NAME, CONF_HOST, CONF_USERNAME, CONF_PASSWORD,
    CONF_MONITORED_CONDITIONS, CONF_VERIFY_SSL)

CONF_PORT = 'port'
CONF_SITE_ID = 'site_id'
CONF_UNIFI_VERSION = 'version'

DEFAULT_NAME = 'UniFi Gateway'
DEFAULT_HOST = 'localhost'
DEFAULT_PORT = 443
DEFAULT_UNIFI_VERSION = 'v5'
DEFAULT_SITE = 'default'
DEFAULT_VERIFY_SSL = False

MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=30)

SENSOR_VPN = 'vpn'
SENSOR_WWW = 'www'
SENSOR_WAN = 'wan'
SENSOR_LAN = 'lan'
SENSOR_WLAN = 'wlan'
SENSOR_ALERTS = 'alerts'
SENSOR_FIRMWARE = 'firmware'

USG_SENSORS = {
    SENSOR_VPN:     ['VPN', '', 'mdi:folder-key-network'],
    SENSOR_WWW:     ['WWW', '', 'mdi:web'],
    SENSOR_WAN:     ['WAN', '', 'mdi:shield-outline'],
    SENSOR_LAN:     ['LAN', '', 'mdi:lan'],
    SENSOR_WLAN:    ['WLAN','', 'mdi:wifi'],
    SENSOR_ALERTS:  ['Alerts', '', 'mdi:information-outline'],
    SENSOR_FIRMWARE:['Firmware Upgradable', '', 'mdi:database-plus']
}

POSSIBLE_MONITORED = [ SENSOR_VPN, SENSOR_WWW, SENSOR_WAN, SENSOR_LAN,
                        SENSOR_WLAN, SENSOR_ALERTS, SENSOR_FIRMWARE ]
DEFAULT_MONITORED = POSSIBLE_MONITORED

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Optional(CONF_HOST, default=DEFAULT_HOST): cv.string,
    vol.Optional(CONF_SITE_ID, default=DEFAULT_SITE): cv.string,
    vol.Required(CONF_PASSWORD): cv.string,
    vol.Required(CONF_USERNAME): cv.string,
    vol.Optional(CONF_UNIFI_VERSION, default=DEFAULT_UNIFI_VERSION): cv.string,
    vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.port,
    vol.Optional(CONF_VERIFY_SSL, default=DEFAULT_VERIFY_SSL):
        vol.Any(cv.boolean, cv.isfile),
    vol.Optional(CONF_MONITORED_CONDITIONS, default=DEFAULT_MONITORED):
        vol.All(cv.ensure_list, [vol.In(POSSIBLE_MONITORED)])
})

class UnifiGatewayFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for UnifiGateway Camera API."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    def __init__(self):
        """Initialize."""
        self.UnifiGateway_config = {}
        self._errors = {}
        self.init_info = None

    async def async_step_user(self, user_input=None):
        """Handle a flow initialized by the user to add a camera."""
        self._errors = {}

        # Uncomment the next 2 lines if only a single instance of the integration is allowed:
        # if self._async_current_entries():
        #     return self.async_abort(reason="single_instance_allowed")

        if user_input is not None:
            data = await self._test_credentials(
                user_input[CONF_NAME],
                user_input[CONF_HOST],
                user_input[CONF_SITE_ID],
                user_input[CONF_USERNAME],
                user_input[CONF_PASSWORD],
                user_input[CONF_UNIFI_VERSION],
                user_input[CONF_PORT],
                user_input[CONF_VERIFY_SSL],
                user_input[CONF_MONITORED_CONDITIONS],
            )
            if data is None:
                self._errors["base"] = "auth"

        return await self._show_config_form_user(user_input)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return UnifiGatewayOptionsFlowHandler(config_entry)

    async def _show_config_form_user(self, user_input):  # pylint: disable=unused-argument
        """Show the configuration form to edit camera name."""
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
                    vol.Optional(CONF_HOST, default=DEFAULT_HOST): cv.string,
                    vol.Optional(CONF_SITE_ID, default=DEFAULT_SITE): cv.string,
                    vol.Required(CONF_PASSWORD): cv.string,
                    vol.Required(CONF_USERNAME): cv.string,
                    vol.Optional(CONF_UNIFI_VERSION, default=DEFAULT_UNIFI_VERSION): cv.string,
                    vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.port,
                    vol.Optional(CONF_VERIFY_SSL, default=DEFAULT_VERIFY_SSL): vol.Any(cv.boolean, cv.isfile),
                    vol.Optional(CONF_MONITORED_CONDITIONS, default=DEFAULT_MONITORED): cv.multi_select([vol.In(POSSIBLE_MONITORED)]),
                }
            ),
            errors=self._errors,
        )

    async def _test_credentials(self, host, username, password, port, version, site_id, ssl_verify):
        """Return name and serialNumber if credentials is valid."""
        session = async_create_clientsession(hass=self.hass, verify_ssl=False)
        try:
            ctrl = Controller(host, username, password, port, version,
                            site_id=site_id, ssl_verify=verify_ssl)
        except APIError as ex:
            _LOGGER.error("Failed to connect to Unifi Security Gateway: %s", ex)
            return False


class UnifiGatewayOptionsFlowHandler(config_entries.OptionsFlow):
    """UnifiGateway config flow options handler."""

    def __init__(self, config_entry):
        """Initialize HACS options flow."""
        self.config_entry = config_entry
        self.options = dict(config_entry.options)

    async def async_step_init(self, user_input=None):  # pylint: disable=unused-argument
        """Manage the options."""
        return await self.async_step_user()

    async def async_step_user(self, user_input=None):
        """Handle a flow initialized by the user."""
        if user_input is not None:
            self.options.update(user_input)
            return await self._update_options()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(x, default=self.options.get(x, True)): bool
                    for x in sorted(PLATFORMS)
                }
            ),
        )

    async def _update_options(self):
        """Update config entry options."""
        return self.async_create_entry(
            title=self.config_entry.data.get(CONF_USERNAME), data=self.options
        )
