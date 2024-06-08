from homeassistant.const import LENGTH_METERS, VOLUME_CUBIC_METERS

CONF_STATIONS = "stations"
VIGICRUES_URL = "https://www.vigicrues.gouv.fr/services/observations.json/index.php"

METRICS_INFO = {
    "H": {"name": "Hauteur", "unit": LENGTH_METERS},
    "Q": {"name": "Debit", "unit": VOLUME_CUBIC_METERS},
}
