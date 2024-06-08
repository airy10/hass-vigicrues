from homeassistant.const import UnitOfVolumeFlowRate, UnitOfLength

CONF_STATIONS = "stations"
VIGICRUES_URL = "https://www.vigicrues.gouv.fr/services/observations.json/index.php"

METRICS_INFO = {
    "H": {"name": "Hauteur", "unit": UnitOfLength.METERS},
    "Q": {"name": "Debit", "unit": UnitOfVolumeFlowRate.CUBIC_METERS_PER_HOUR},
}
