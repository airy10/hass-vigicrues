"""Platform for vigicrues sensor integration."""
from datetime import timedelta
import logging
import requests
import voluptuous as vol

from homeassistant.helpers.entity import Entity
from homeassistant.components.sensor import PLATFORM_SCHEMA
import homeassistant.helpers.config_validation as cv
from homeassistant.const import ATTR_LATITUDE, ATTR_LONGITUDE
from homeassistant.util import slugify

from .const import CONF_STATIONS, VIGICRUES_URL, HUBEAU_URL, METRICS_INFO

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(minutes=30)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {vol.Required(CONF_STATIONS): vol.All(cv.ensure_list, [cv.string])}
)


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the sensor."""

    sensors = []
    for station_id in config.get(CONF_STATIONS):
        station = Vigicrues(station_id)
        station.update()
        sensors.append(VigicruesHeightSensor(station))
        sensors.append(VigicruesWaterFlowRateSensor(station))

    add_entities(sensors, True)


class VigicruesSensor(Entity):
    """Representation of a Vigicrues Sensor."""

    def __init__(self, station, _type):
        """Initialize the sensor."""
        self.station = station
        self._type = _type
        self._name = f"Vigicrues {self.station.name} {self.name_type()}"
        self._attr_extra_state_attributes = {
            ATTR_LONGITUDE: self.station.coordinates[0],
            ATTR_LATITUDE: self.station.coordinates[1],
        }

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def unique_id(self):
        """Return the unique id of the sensor."""
        return slugify(self._name)

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return METRICS_INFO.get(self._type).get("unit")

    def name_type(self):
        """Return the name of the type."""
        return METRICS_INFO.get(self._type).get("name")


class VigicruesHeightSensor(VigicruesSensor):
    """Representation of Vigicrues Height Sensor."""

    def __init__(self, station):
        """Initialize the sensor."""
        super().__init__(station, "H")
        self._state = self.station.height

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    def update(self):
        """Fetch new state data for the sensor."""
        self.station.update()
        self._state = self.station.height


class VigicruesWaterFlowRateSensor(VigicruesSensor):
    """Representation of Vigicrues WaterFlow Sensor."""

    def __init__(self, station):
        """Initialize the sensor."""
        super().__init__(station, "Q")
        self._state = self.station.waterflowrate

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    def update(self):
        """Fetch new state data for the sensor."""
        self.station.update()
        self._state = self.station.waterflowrate


class Vigicrues(object):
    """vigicrues object."""

    def __init__(self, station_id):
        """Initialize"""
        self.station_id = station_id
        self.name = self.get_name()
        self.waterflowrate = None
        self.height = None
        self.coordinates = self.get_coordinates()

    def get_height(self):
        return self.__get_last_point("H")

    def get_waterflowrate(self):
        return self.__get_last_point("Q")

    def get_name(self):
        return self.get_data("H").get("Serie").get("LbStationHydro")

    def get_data(self, _type):
        params = {"CdStationHydro": self.station_id, "GrdSerie": _type}

        try:
            data = requests.get(VIGICRUES_URL, params=params).json()
        except Exception:
            _LOGGER.error("Unable to get data from %s", VIGICRUES_URL)
            raise Exception("Unable to get data")

        return data

    def get_coordinates(self):
        params = {"code_station": self.station_id , "size": 1}

        try:
            data = requests.get(HUBEAU_URL, params=params).json()
        except Exception:
            _LOGGER.error("Unable to get coordinates from %s", HUBEAU_URL)
            raise Exception("Unable to get data")

        return data.get('data')[0].get('geometry').get('coordinates')

    def __get_last_point(self, _type):
        try:
            return self.get_data(_type)["Serie"]["ObssHydro"][-1]["ResObsHydro"]
        except Exception:
            return

    def update(self):
        self.waterflowrate = self.get_waterflowrate()
        self.height = self.get_height()
