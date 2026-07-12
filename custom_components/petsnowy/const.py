"""Constants for the PetSnowy integration."""

DOMAIN = "petsnowy"

CONF_DEVICE_TYPE = "device_type"
CONF_DEVICE_ID = "device_id"
CONF_ADDRESS = "address"
CONF_LOCAL_KEY = "local_key"
CONF_VERSION = "version"

CONF_WEIGHT_OFFSET = "weight_offset"
CONF_EXTERNAL_MOTION_SENSOR = "external_motion_sensor"
CONF_PIR_GRACE_MINUTES = "pir_grace_minutes"

# Tuya Cloud credentials (used by cloud-polling devices such as the OilClear).
CONF_REGION = "region"
CONF_CLIENT_ID = "client_id"
CONF_CLIENT_SECRET = "client_secret"

# Data-centre regions accepted by tinytuya.Cloud.
TUYA_REGIONS: tuple[str, ...] = ("eu", "us", "cn", "in")
DEFAULT_REGION = "eu"

# Volume unit for the OilClear drinking-data sensors (options flow).
CONF_VOLUME_UNIT = "volume_unit"
VOLUME_UNIT_ML = "ml"
VOLUME_UNIT_OZ = "oz"
DEFAULT_VOLUME_UNIT = VOLUME_UNIT_ML

DEFAULT_PIR_GRACE_MINUTES = 5

DEVICE_TYPE_LITTERBOX = "litterbox"
DEVICE_TYPE_FOUNTAIN = "fountain"
DEVICE_TYPE_OILCLEAR = "oilclear"
DEVICE_TYPE_PURIFIER = "purifier"
DEVICE_TYPE_FEEDER = "feeder"

DEVICE_TYPES: dict[str, str] = {
    DEVICE_TYPE_LITTERBOX: "Snow+ Litterbox",
    DEVICE_TYPE_FOUNTAIN: "Water Fountain",
    DEVICE_TYPE_OILCLEAR: "OilClear AI Water Fountain",
    DEVICE_TYPE_PURIFIER: "Air Purifier",
    DEVICE_TYPE_FEEDER: "Pet Feeder",
}

DEFAULT_VERSIONS: dict[str, float] = {
    DEVICE_TYPE_LITTERBOX: 3.4,
    DEVICE_TYPE_FOUNTAIN: 3.3,
    DEVICE_TYPE_OILCLEAR: 3.3,
    DEVICE_TYPE_PURIFIER: 3.4,
    DEVICE_TYPE_FEEDER: 3.3,
}

PLATFORMS: list[str] = [
    "binary_sensor",
    "button",
    "fan",
    "number",
    "select",
    "sensor",
    "switch",
]

DEFAULT_SCAN_INTERVAL = 30
