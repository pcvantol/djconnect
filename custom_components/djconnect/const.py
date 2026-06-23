"""Constants for DJConnect."""
from __future__ import annotations

DOMAIN = "djconnect"
NAME = "DJConnect"
VERSION = "3.1.82"

API_BASE = "/api/djconnect"
API_PAIR = f"{API_BASE}/pair"
API_VOICE = f"{API_BASE}/voice"
API_COMMAND = f"{API_BASE}/command"
API_STATUS = f"{API_BASE}/status"
API_EVENT = f"{API_BASE}/event"
API_ASK_DJ = f"{API_BASE}/ask_dj"
API_ASK_DJ_MESSAGE = f"{API_ASK_DJ}/message"
API_ASK_DJ_IDLE_SUGGESTION = f"{API_ASK_DJ}/idle_suggestion"
API_ASK_DJ_HISTORY = f"{API_ASK_DJ}/history"
API_ASK_DJ_HISTORY_CLEAR = f"{API_ASK_DJ_HISTORY}/clear"
API_ASK_DJ_CLEAR = f"{API_ASK_DJ}/clear"
API_ASK_DJ_HISTORY_STATE = f"{API_ASK_DJ}/history_state"
API_IMAGE_PROXY_BASE = f"{API_BASE}/image_proxy"
API_IMAGE_PROXY = f"{API_IMAGE_PROXY_BASE}/{{token}}"
API_PUSH_REGISTER = f"{API_BASE}/push/register"
API_PUSH_UNREGISTER = f"{API_BASE}/push/unregister"
API_TTS_BASE = f"{API_BASE}/tts"
API_TTS = f"{API_TTS_BASE}/{{token}}.{{extension}}"
API_SPOTIFY_CALLBACK = f"{API_BASE}/spotify/callback"

CONF_DEVICE_ID = "device_id"
CONF_DEVICE_NAME = "device_name"
CONF_DEVICE_TOKEN = "device_token"
CONF_DEVICE_LANGUAGE = "device_language"
CONF_CLIENT_TYPE = "client_type"
CONF_LOCAL_URL = "local_url"
CONF_HA_EXTERNAL_URL = "ha_external_url"
CONF_PAIR_CODE = "pair_code"
CONF_SETUP_METHOD = "setup_method"
CONF_BLE_ADDRESS = "ble_address"
CONF_WIFI_SSID = "wifi_ssid"
CONF_WIFI_PASSWORD = "wifi_password"
CONF_API_BASE_URL = "api_base_url"
CONF_HA_INSTALL_ID = "ha_install_id"
CONF_DJCONNECT_INSTALL_TOKEN = "djconnect_install_token"
CONF_CENTRAL_API_BOOTSTRAP_PROOF = "central_api_bootstrap_proof"
CONF_CENTRAL_API_BOOTSTRAP_PROOF_EXPIRES_AT = "central_api_bootstrap_proof_expires_at"

CONF_SPOTIFY_CLIENT_ID = "spotify_client_id"
CONF_SPOTIFY_REFRESH_TOKEN = "spotify_refresh_token"
CONF_SPOTIFY_MARKET = "spotify_market"
CONF_SPOTIFY_SCOPES = "spotify_scopes"
CONF_SPOTIFY_SOURCE = "spotify_source"
CONF_LIKED_PROXY = "liked_proxy_playlist_uri"

CONF_ASSIST_PIPELINE_ID = "assist_pipeline_id"
CONF_STT_ENGINE = "stt_engine"
CONF_TTS_ENGINE = "tts_engine"
CONF_TTS_LANGUAGE = "tts_language"
CONF_TTS_VOICE = "tts_voice"
CONF_DJ_RESPONSE_ENABLED = "dj_response_enabled"
CONF_DJ_RESPONSE_TTL_SECONDS = "dj_response_ttl_seconds"
CONF_DJ_RESPONSE_PROMPT_PRESET = "dj_response_prompt_preset"
CONF_DJ_RESPONSE_PROMPT = "dj_response_prompt"
CONF_SMART_HOME_CONTEXT_ENTITIES = "smart_home_context_entities"

CONF_MAX_AUDIO_BYTES = "max_audio_bytes"

CONF_FIRMWARE_REPO = "firmware_repo"
CONF_FIRMWARE_DEVICE = "firmware_device"
CONF_FIRMWARE_CHANNEL = "firmware_channel"
CONF_ALLOW_OTA_ON_BATTERY = "allow_ota_on_battery"
CONF_MIN_BATTERY_FOR_OTA = "min_battery_for_ota"

DEFAULT_DEVICE_NAME = "DJConnect"
DEFAULT_DEVICE_LANGUAGE = "en"
CLIENT_TYPE_ESP32 = "esp32"
CLIENT_TYPE_IOS = "ios"
CLIENT_TYPE_MACOS = "macos"
CLIENT_TYPE_WATCHOS = "watchos"
CLIENT_TYPE_RASPBERRY_PI = "raspberry_pi"
CLIENT_TYPE_CONVERSATION_AGENT = "conversation_agent"
DEFAULT_CLIENT_TYPE = CLIENT_TYPE_ESP32
CLIENT_TYPES = [
    CLIENT_TYPE_IOS,
    CLIENT_TYPE_MACOS,
    CLIENT_TYPE_WATCHOS,
    CLIENT_TYPE_RASPBERRY_PI,
    CLIENT_TYPE_ESP32,
]
CLIENT_TYPE_NAMES = {
    CLIENT_TYPE_IOS: "iOS app",
    CLIENT_TYPE_MACOS: "macOS app",
    CLIENT_TYPE_WATCHOS: "Apple Watch app",
    CLIENT_TYPE_RASPBERRY_PI: "Linux/Raspberry Pi client",
    CLIENT_TYPE_ESP32: "ESP32 device",
}
SETUP_METHOD_PAIR_EXISTING = "pair_existing"
SETUP_METHOD_BLE_WIFI = "ble_wifi"
SETUP_METHOD_CONVERSATION_AGENT = "conversation_agent"
DEFAULT_SETUP_METHOD = SETUP_METHOD_CONVERSATION_AGENT
DEFAULT_API_BASE_URL = "https://api.djconnect.dev"
DEFAULT_SPOTIFY_MARKET = "NL"
DEFAULT_MAX_AUDIO_BYTES = 2_000_000
DEFAULT_FIRMWARE_REPO = "pcvantol/djconnect-firmware"
DEFAULT_FIRMWARE_DEVICE = "lilygo-t-embed-s3"
DEFAULT_FIRMWARE_CHANNEL = "stable"
FIRMWARE_CHANNEL_STABLE = "stable"
FIRMWARE_CHANNEL_BETA = "beta"
FIRMWARE_CHANNELS = [FIRMWARE_CHANNEL_STABLE, FIRMWARE_CHANNEL_BETA]
DEFAULT_MIN_BATTERY_FOR_OTA = 40

DEFAULT_ASSIST_PIPELINE_ID = ""
DEFAULT_STT_ENGINE = ""
DEFAULT_TTS_ENGINE = ""
DEFAULT_TTS_LANGUAGE = "nl-NL"
DEFAULT_TTS_VOICE = ""
DEFAULT_DJ_RESPONSE_ENABLED = True
DEFAULT_DJ_RESPONSE_TTL_SECONDS = 60 * 60
DJ_RESPONSE_PROMPT_PRESET_NEUTRAL = "neutral_business"
DJ_RESPONSE_PROMPT_PRESET_WARM = "warm_personal"
DJ_RESPONSE_PROMPT_PRESET_HUMOR = "humorous_witty"
DJ_RESPONSE_PROMPT_PRESET_CUSTOM = "custom"
DJ_RESPONSE_PROMPT_PRESETS = [
    DJ_RESPONSE_PROMPT_PRESET_NEUTRAL,
    DJ_RESPONSE_PROMPT_PRESET_WARM,
    DJ_RESPONSE_PROMPT_PRESET_HUMOR,
    DJ_RESPONSE_PROMPT_PRESET_CUSTOM,
]
DJ_RESPONSE_PROMPT_TEXTS = {
    DJ_RESPONSE_PROMPT_PRESET_NEUTRAL: (
        "Noem de artiest, het album en het nummer.\n"
        "Houd de aankondiging kort, duidelijk en zakelijk.\n"
        "Gebruik geen grapjes of overdreven enthousiasme."
    ),
    DJ_RESPONSE_PROMPT_PRESET_WARM: (
        "Noem de artiest, het album en het nummer.\n"
        "Geef een leuk feitje over de artiest.\n"
        "Klink warm en persoonlijk."
    ),
    DJ_RESPONSE_PROMPT_PRESET_HUMOR: (
        "Noem de artiest, het album en het nummer.\n"
        "Maak de aankondiging luchtig, humoristisch en gevat.\n"
        "Gebruik maximaal een korte grap en blijf vriendelijk."
    ),
}
DEFAULT_DJ_RESPONSE_PROMPT = DJ_RESPONSE_PROMPT_TEXTS[
    DJ_RESPONSE_PROMPT_PRESET_WARM
]
SPOTIFY_SCOPES = [
    "user-read-playback-state",
    "user-modify-playback-state",
    "user-read-currently-playing",
    "user-library-read",
    "playlist-read-private",
    "playlist-read-collaborative",
    "playlist-modify-private",
    "playlist-modify-public",
    "user-read-recently-played",
    "user-top-read",
]
DEFAULT_SPOTIFY_SCOPES = " ".join(SPOTIFY_SCOPES)

PLATFORMS = ["sensor", "button", "number", "select", "switch", "update", "media_player", "conversation"]

# Spotify OAuth/PKCE direct callback support
SPOTIFY_CALLBACK_PATH = API_SPOTIFY_CALLBACK
