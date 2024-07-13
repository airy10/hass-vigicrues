from homeassistant.const import UnitOfVolumeFlowRate, UnitOfLength

CONF_STATIONS = "stations"
VIGICRUES_URL = "https://www.vigicrues.gouv.fr"
VIGICRUES_PICTURE = VIGICRUES_URL + "/ftp/niv3/photos"
VIGICRUES_API = VIGICRUES_URL + "/services/observations.json/index.php"
HUBEAU_URL = "https://hubeau.eaufrance.fr/api/v1/hydrometrie/referentiel/stations"


METRICS_INFO = {
    "H": {"name": "Hauteur", "unit": UnitOfLength.METERS},
    "Q": {"name": "Debit", "unit": UnitOfVolumeFlowRate.CUBIC_METERS_PER_HOUR},
}
