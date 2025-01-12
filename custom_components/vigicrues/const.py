from homeassistant.const import UnitOfLength

CONF_STATIONS = "stations"
VIGICRUES_URL = "https://www.vigicrues.gouv.fr"
VIGICRUES_PICTURE = f"{VIGICRUES_URL}/ftp/niv3/photos"
VIGICRUES_API = f"{VIGICRUES_URL}/services/observations.json/index.php"
HUBEAU_API = "https://hubeau.eaufrance.fr/api/v1/hydrometrie/referentiel/stations"


METRICS_INFO = {
    "H": {"name": "Hauteur", "unit": UnitOfLength.METERS},
    "Q": {"name": "Debit", "unit": "m³/s"},
}
