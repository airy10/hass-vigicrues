"""Platform for vigicrues sensor integration."""
from datetime import timedelta
import logging
import requests
import voluptuous as vol
import math

from homeassistant.helpers.entity import Entity
from homeassistant.components.sensor import PLATFORM_SCHEMA, SensorDeviceClass
import homeassistant.helpers.config_validation as cv
from homeassistant.const import ATTR_LATITUDE, ATTR_LONGITUDE
from homeassistant.util import slugify

from .const import CONF_STATIONS, VIGICRUES_OBSERVATIONS_API, VIGICRUES_STATION_API, METRICS_INFO, VIGICRUES_PICTURE

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


def lambert93_to_wgs84(x, y):
    """
    Converts Lambert 93 (RGF93) coordinates to WGS 84 geographic coordinates (latitude and longitude).

    This function implements the conversion using the official Lambert 93 projection parameters
    provided by the French Institut Géographique National (IGN). It calculates the latitude and
    longitude in decimal degrees without using external libraries.

    Args:
        x (float): The x-coordinate in the Lambert 93 projection (in meters).
        y (float): The y-coordinate in the Lambert 93 projection (in meters).

    Returns:
        tuple: A tuple containing:
            - latitude (float): The latitude in decimal degrees.
            - longitude (float): The longitude in decimal degrees.

    Example:
        >>> x, y = 657256, 6853507
        >>> latitude, longitude = lambert93_to_wgs84(x, y)
        >>> print(f"Latitude: {latitude:.6f}, Longitude: {longitude:.6f}")
        Latitude: 48.780238, Longitude: 2.418295
    """
    # Constants for Lambert 93 (RGF93)
    GRS80_E = 0.0818191910428158  # Eccentricity of the GRS80 ellipsoid
    GRS80_A = 6378137.0  # Semi-major axis (in meters)

    # Lambert 93 parameters
    n = 0.7256077650532670
    c = 11754255.4261
    xs = 700000.0
    ys = 12655612.0499
    lon_meridian_origin = 3 * math.pi / 180  # In radians

    # Intermediate calculations
    x_diff = x - xs
    y_diff = ys - y
    r = math.sqrt(x_diff**2 + y_diff**2)
    gamma = math.atan2(x_diff, -y_diff)
    l = -math.log(r / c) / n

    # Isometric latitude calculation
    lat_iso = math.asin(math.tanh(l))
    for _ in range(5):  # Iterative approximation
        lat_iso = math.asin(math.tanh(l + GRS80_E * math.atanh(GRS80_E * math.sin(lat_iso))))

    # Final latitude and longitude
    latitude = math.degrees(lat_iso)
    longitude = math.degrees(gamma / n + lon_meridian_origin)

    return latitude, longitude


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
        self._attr_entity_picture = station.get_entity_picture()


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

    _attr_device_class = SensorDeviceClass.DISTANCE
    _attr_icon = "mdi:waves-arrow-up"

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

    _attr_device_class = SensorDeviceClass.VOLUME_FLOW_RATE
    _attr_icon = "mdi:waves"

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
        serie_data = self.get_data("H").get("Serie")
        return f"{serie_data.get('LbStationHydro')} - {serie_data.get('CdStationHydro')}"

    def get_data(self, _type):
        params = {"CdStationHydro": self.station_id, "GrdSerie": _type}

        try:
            data = requests.get(VIGICRUES_OBSERVATIONS_API, params=params).json()
            data.raise_for_status()
        except Exception:
            _LOGGER.error("Unable to get data from %s", VIGICRUES_OBSERVATIONS_API)
            raise Exception("Unable to get data")

        return data

    def get_coordinates(self):
        """ Get coordinates from VIGICRUE and transform them in longitude and latitute """
        params = {"CdStationHydro": self.station_id}

        try:
            data = requests.get(VIGICRUES_STATION_API, params=params).json()
            data.raise_for_status()
        except Exception:
            _LOGGER.error("Unable to get coordinates from %s", VIGICRUES_STATION_API)
            raise Exception("Unable to get data")

        coordstation = data.get("CoordStationHydro")
        coordx, coordy = coordstation.get("CoordXStationHydro"), coordstation.get("CoordYStationHydro")

        # Coordinate transformation
        latitude, longitude = lambert93_to_wgs84(coordx, coordy)

        return (longitude, latitude)

    def get_entity_picture(self):
        url_picture = f"{VIGICRUES_PICTURE}/photo_{self.station_id}.jpg"
        try:
            response = requests.get(url_picture)
            response.raise_for_status()
        except Exception:
            return ""
        else:
            return url_picture

    def __get_last_point(self, _type):
        try:
            return self.get_data(_type)["Serie"]["ObssHydro"][-1]["ResObsHydro"]
        except Exception:
            return

    def update(self):
        self.waterflowrate = self.get_waterflowrate()
        self.height = self.get_height()
