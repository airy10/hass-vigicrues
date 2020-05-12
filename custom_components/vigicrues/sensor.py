"""Platform for vigicrues sensor integration."""

import requests
import voluptuous as vol

from homeassistant.const import LENGTH_METERS, VOLUME_CUBIC_METERS
from homeassistant.helpers.entity import Entity

from homeassistant.helpers import config_validation as cv
from homeassistant.components.sensor import PLATFORM_SCHEMA


CONF_STATION = "station"
VIGICRUES_URL = "https://www.vigicrues.gouv.fr/services/observations.json"


# Validation of the user's configuration
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({vol.Required(CONF_STATION): cv.string})

NAME = {"H": "Hauteur", "Q": "Debit"}


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the sensor platform."""
    station = config[CONF_STATION]

    add_entities(
        [VigicruesHeightSensor(station), VigicruesWaterFlowRateSensor(station)],
    )


class VigicruesSensor(Entity):
    """Representation of a Sensor."""

    def __init__(self, station, _type):
        """Initialize the sensor."""
        self._state = None
        self._station = station
        self.client = Vigicrues(station)
        self._name = f"Vigicrues {self.client.name} {NAME[_type]}"
        self._type = _type

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state


class VigicruesHeightSensor(VigicruesSensor):
    """Representation of Vigicrues Height Sensor."""

    def __init__(self, station):
        """Initialize the sensor."""
        super().__init__(station, "H")

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return LENGTH_METERS

    def update(self):
        """Fetch new state data for the sensor."""
        self._state = self.client.height


class VigicruesWaterFlowRateSensor(VigicruesSensor):
    """Representation of Vigicrues WaterFlow Sensor."""

    def __init__(self, station):
        """Initialize the sensor."""
        super().__init__(station, "Q")

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return VOLUME_CUBIC_METERS

    def update(self):
        """Fetch new state data for the sensor."""
        self._state = self.client.waterflowrate


class Vigicrues(object):
    """vigicrues object."""

    def __init__(self, station):
        """Initialize"""
        self.station = station
        self.name = self.get_name()
        self.waterflowrate = self.get_waterflowrate()
        self.height = self.get_height()

    def get_height(self):
        return self.__get_last_point("H")

    def get_waterflowrate(self):
        return self.__get_last_point("Q")

    def get_name(self):
        return self.get_data("H").get("Serie").get("LbStationHydro")

    def get_data(self, _type):
        params = {"CdStationHydro": self.station, "GrdSerie": _type}

        try:
            data = requests.get(VIGICRUES_URL, params=params).json()
        except Exception:
            raise Exception("Unable to get data")

        return data

    def __get_last_point(self, _type):
        try:
            return self.get_data(_type)["Serie"]["ObssHydro"][-1]["ResObsHydro"]
        except Exception:
            return
