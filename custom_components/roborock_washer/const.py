"""Constants for Roborock Washer integration."""
from datetime import timedelta
from typing import Final

DOMAIN: Final = "roborock_washer"

# Update intervals based on protocol type
UPDATE_INTERVAL_FREQUENT: Final = timedelta(minutes=1)  # STATE, WASHING_LEFT, DOORLOCK_STATE, COUNTDOWN
UPDATE_INTERVAL_INFREQUENT: Final = timedelta(hours=6)  # ERROR, CUSTOM_PARAM_GET, TIMES_AFTER_CLEAN, DETERGENT_EMPTY, SOFTENER_EMPTY

# Config flow
CONF_USERNAME: Final = "username"
CONF_PASSWORD: Final = "password"
CONF_COUNTRY_CODE: Final = "country_code"
CONF_USER_DATA: Final = "user_data"
CONF_BASE_URL: Final = "base_url"
CONF_ENTRY_CODE: Final = "code"

# Device traits - Updated to match Zeo protocol
TRAIT_STATUS: Final = "status"
TRAIT_WASH_PROGRAM: Final = "wash_program"
TRAIT_WASH_TEMP: Final = "wash_temp"
TRAIT_SPIN_SPEED: Final = "spin_speed"
TRAIT_LOAD_WEIGHT: Final = "load_weight"
TRAIT_ERROR: Final = "error"
TRAIT_DOOR_LOCK_STATE: Final = "door_lock_state"
TRAIT_DETERGENT_EMPTY: Final = "detergent_empty"
# TRAIT_SOFTENER_EMPTY: Final = "softener_empty"  # 不支持
TRAIT_DOOR_OPEN_WARNING: Final = "door_open_warning"
TRAIT_ADD_LAUNDRY: Final = "add_laundry"
# TRAIT_CHILD_LOCK: Final = "child_lock"  # 不支持
TRAIT_SOUND: Final = "sound"
# TRAIT_DETERGENT_SET: Final = "detergent_set"  # 不支持
# TRAIT_SOFTENER_SET: Final = "softener_set"  # 不支持
# TRAIT_LIGHT_SETTING: Final = "light_setting"  # 不支持
TRAIT_MODE: Final = "mode"
TRAIT_PROGRAM: Final = "program"
TRAIT_TEMP: Final = "temp"
TRAIT_RINSE_TIMES: Final = "rinse_times"
TRAIT_SPIN_LEVEL: Final = "spin_level"
TRAIT_DRYING_MODE: Final = "drying_mode"
TRAIT_DETERGENT_TYPE: Final = "detergent_type"
# TRAIT_SOFTENER_TYPE: Final = "softener_type"  # 不支持
TRAIT_COUNTDOWN: Final = "countdown"
# TRAIT_CUSTOM_PARAM_GET: Final = "custom_param_get"  # 不支持
TRAIT_WASHING_LEFT: Final = "washing_left"
TRAIT_TIMES_AFTER_CLEAN: Final = "times_after_clean"
TRAIT_START: Final = "start"
TRAIT_PAUSE: Final = "pause"
TRAIT_SHUTDOWN: Final = "shutdown"

# Services - Updated to match Zeo protocol
SERVICE_START_WASH: Final = "start_wash"
SERVICE_PAUSE_WASH: Final = "pause_wash"
SERVICE_STOP_WASH: Final = "stop_wash"
# SERVICE_SET_CHILD_LOCK: Final = "set_child_lock"  # 不支持
SERVICE_SET_SOUND: Final = "set_sound"
# SERVICE_CUSTOM_PARAM_SAVE: Final = "custom_param_save"  # 不支持
# SERVICE_DEFAULT_SETTING: Final = "default_setting"  # 不支持
# SERVICE_SET_DETERGENT: Final = "set_detergent"  # 不支持
# SERVICE_SET_SOFTENER: Final = "set_softener"  # 不支持
SERVICE_SET_LIGHT: Final = "set_light"
SERVICE_SET_MODE: Final = "set_mode"
SERVICE_SET_PROGRAM: Final = "set_program"
SERVICE_SET_TEMP: Final = "set_temp"
SERVICE_SET_RINSE_TIMES: Final = "set_rinse_times"
SERVICE_SET_SPIN_LEVEL: Final = "set_spin_level"
SERVICE_SET_DRYING_MODE: Final = "set_drying_mode"
SERVICE_SET_DETERGENT_TYPE: Final = "set_detergent_type"
# SERVICE_SET_SOFTENER_TYPE: Final = "set_softener_type"  # 不支持
SERVICE_SET_COUNTDOWN: Final = "set_countdown"