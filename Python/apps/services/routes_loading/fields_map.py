from shared.database import settings
from shared.models.upoader_fields_config import UploaderFieldsConfig
from shared.resources import Resources


def get_fields_config_from_file():
    return UploaderFieldsConfig(
        **Resources.get(settings.DEFAULT_UPLOADER_FIELDS_CONFIG_RESOURCE_NAME, scope="backend_admin").read_json(),
    )
