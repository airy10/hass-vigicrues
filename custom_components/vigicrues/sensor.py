"""Platform for vigicrues sensor integration."""
from datetime import timedelta
import logging
import requests
import voluptuous as vol
import math

from homeassistant.helpers.entity import Entity
from homeassistant.components.sensor import PLATFORM_SCHEMA, SensorDeviceClass, SensorStateClass, SensorEntity
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
    Converts Lambert 93 coordinates (x, y) to WGS84 geographic coordinates (latitude, longitude).

    Parameters:
        x (float): The X-coordinate in Lambert 93 (meters).
        y (float): The Y-coordinate in Lambert 93 (meters).

    Returns:
        tuple: A tuple containing:
            - latitude (float): Latitude in WGS84 (degrees).
            - longitude (float): Longitude in WGS84 (degrees).
    """
    # Constants for the Lambert 93 projection
    a = 6378137.0  # Semi-major axis of the GRS80 ellipsoid
    e = 0.0818191910428158  # Ellipsoid eccentricity
    n = 0.7256077650532670  # Projection scale factor
    c = 11754255.4261  # Projection constant
    Xs = 700000.0  # X-coordinate of the false origin
    Ys = 12655612.0499  # Y-coordinate of the false origin
    lambda0 = 3 * math.pi / 180  # Central meridian (3°E in radians)

    # Calculate the polar radius (distance to the origin in the Lambert 93 projection)
    r = math.sqrt((x - Xs)**2 + (y - Ys)**2)

    # Calculate the polar angle (angle from the origin)
    gamma = math.atan((x - Xs) / (Ys - y))

    # Compute the isometric latitude
    l = -math.log(abs(r / c)) / n
    lat_iso = 2 * math.atan(math.exp(l)) - math.pi / 2

    # Iteratively compute the geographic latitude
    phi = lat_iso
    for _ in range(7):  # Use 7 iterations to ensure precision
        phi = 2 * math.atan(
            ((1 + e * math.sin(phi)) / (1 - e * math.sin(phi)))**(e / 2) * math.exp(l)
        ) - math.pi / 2

    # Compute the geographic longitude
    lon = lambda0 + gamma / n
    lat = phi

    # Convert latitude and longitude from radians to degrees
    return math.degrees(lat), math.degrees(lon)


class VigicruesSensor(SensorEntity):
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
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = METRICS_INFO.get(_type).get("unit")


    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def unique_id(self):
        """Return the unique id of the sensor."""
        return slugify(self._name)

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
        self._attr_native_value = self.station.height

    def update(self):
        """Fetch new state data for the sensor."""
        self.station.update()
        self._attr_native_value = self.station.height


class VigicruesWaterFlowRateSensor(VigicruesSensor):
    """Representation of Vigicrues WaterFlow Sensor."""

    _attr_device_class = SensorDeviceClass.VOLUME_FLOW_RATE
    _attr_icon = "mdi:waves"

    def __init__(self, station):
        """Initialize the sensor."""
        super().__init__(station, "Q")
        self._attr_native_value = self.station.waterflowrate * 3600 if self.station.waterflowrate is not None else None

    def update(self):
        """Fetch new state data for the sensor."""
        self.station.update()
        self._attr_native_value = self.station.waterflowrate * 3600 if self.station.waterflowrate is not None else None

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
            data = requests.get(VIGICRUES_OBSERVATIONS_API, params=params)
            data.raise_for_status()
        except Exception:
            _LOGGER.error("Unable to get data from %s", VIGICRUES_OBSERVATIONS_API)
            raise Exception("Unable to get data")

        return data.json()

    def get_coordinates(self):
        """ Get coordinates from VIGICRUE and transform them in longitude and latitute """
        params = {"CdStationHydro": self.station_id}

        try:
            data = requests.get(VIGICRUES_STATION_API, params=params)
            data.raise_for_status()
        except Exception:
            _LOGGER.error("Unable to get coordinates from %s", VIGICRUES_STATION_API)
            raise Exception("Unable to get data")

        coordstation = data.json().get("CoordStationHydro")
        coordx, coordy = coordstation.get("CoordXStationHydro"), coordstation.get("CoordYStationHydro")

        # Coordinate transformation
        latitude, longitude = lambert93_to_wgs84(int(coordx), int(coordy))

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
