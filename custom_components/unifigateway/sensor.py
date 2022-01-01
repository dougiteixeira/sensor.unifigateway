"""
Support for Unifi Security Gateway Units.

For more details about this platform, please refer to the documentation at
https://github.com/custom-components/sensor.unifigateway

"""

import logging
import voluptuous as vol
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import Entity
import homeassistant.helpers.config_validation as cv
from homeassistant.util import Throttle
from homeassistant.components.sensor import PLATFORM_SCHEMA
from config_flow import (
    CONF_NAME,
    CONF_HOST,
    CONF_USERNAME,
    CONF_PASSWORD,
    CONF_SITE_ID,
    CONF_UNIFI_VERSION,
    CONF_PORT,
    CONF_MONITORED_CONDITIONS,
    CONF_VERIFY_SSL
)

__version__ = '0.3.5'

_LOGGER = logging.getLogger(__name__)

def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the Unifi sensor."""
    from pyunifi.controller import Controller, APIError

    name = config.get(CONF_NAME)
    host = config.get(CONF_HOST)
    username = config.get(CONF_USERNAME)
    password = config.get(CONF_PASSWORD)
    site_id = config.get(CONF_SITE_ID)
    version = config.get(CONF_UNIFI_VERSION)
    port = config.get(CONF_PORT)
    verify_ssl = config.get(CONF_VERIFY_SSL)

    try:
        ctrl = Controller(host, username, password, port, version,
                          site_id=site_id, ssl_verify=verify_ssl)
    except APIError as ex:
        _LOGGER.error("Failed to connect to Unifi Security Gateway: %s", ex)
        return False

    for sensor in config.get(CONF_MONITORED_CONDITIONS):
        add_entities([UnifiGatewaySensor(hass, ctrl, name, sensor)], True)

class UnifiGatewaySensor(Entity):
    """Implementation of a UniFi Gateway sensor."""

    def __init__(self, hass, ctrl, name, sensor):
        """Initialize the sensor."""
        self._hass = hass
        self._ctrl = ctrl
        self._name = name + ' ' + USG_SENSORS[sensor][0]
        self._sensor = sensor
        self._state = None
        self._alldata = None
        self._data = None
        self._attributes = {}

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def icon(self):
        """Icon to use in the frontend, if any."""
        return USG_SENSORS[self._sensor][2]

    @property
    def state(self):
        """Return the state of the device."""
        return self._state

    @property
    def state_attributes(self):
        """Return the device state attributes."""
        return self._attributes

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update(self):
        """Set up the sensor."""
        from pyunifi.controller import APIError

        if self._sensor == SENSOR_ALERTS:
          self._attributes = {}

          try:
              unarchived_alerts = self._ctrl.get_alerts()
          except APIError as ex:
              _LOGGER.error("Failed to access alerts info: %s", ex)
          else:
              for index, alert in enumerate(unarchived_alerts,start=1):
                  if not alert['archived']:
                      self._attributes[str(index)] = alert

              self._state = len(self._attributes)

        elif self._sensor == SENSOR_FIRMWARE:
          self._attributes = {}
          self._state = 0

          try:
            aps = self._ctrl.get_aps()
          except APIError as ex:
            _LOGGER.error("Failed to scan aps: %s", ex)
          else:
            # Set the attributes based on device name - this may not be unique
            # but is user-readability preferred
            for devices in aps:
              if devices.get('upgradable'):
                  self._attributes[devices['name']] = devices['upgradable']
                  self._state += 1

        else:
          # get_healthinfo() call made for each of 4 sensors - should only be for 1
          try:
              # Check that function exists...potential errors on startup otherwise
              if hasattr(self._ctrl,'get_healthinfo'):
                  self._alldata = self._ctrl.get_healthinfo()

                  for sub in self._alldata:
                      if sub['subsystem'] == self._sensor:
                          self._data = sub
                          self._state = sub['status'].upper()
                          for attr in sub:
                              self._attributes[attr] = sub[attr]

              else:
                  _LOGGER.error("no healthinfo attribute for controller")
          except APIError as ex:
              _LOGGER.error("Failed to access health info: %s", ex)
