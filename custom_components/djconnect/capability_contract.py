"""Transport-independent platform capability advertisement, never an access grant."""

from .domain.profile.dj_settings import SETTINGS_VERSION


def _platform_capabilities() -> dict[str, bool]:
    """Return platform capability flags that are independent of transport."""
    return {
        "profiles": True,
        "explicit_profile_selection": True,
        "private_sessions": True,
        "profile_export": True,
        "request_context": True,
        "voice_endpoint_request_context": True,
        "voice_endpoint_mappings": True,
        "session_conversation_history": True,
        "ask_dj_contextual_dialogue": True,
        "ask_dj_examples": True,
        "ask_dj_contextual_exploration": True,
        "session_mood_music_feedback": True,
        "moment_track_insight_navigation_v1": True,
        "session_flow_text_search": True,
        "active_session_mood": True,
        "active_session_persona": True,
        "active_session_presence": True,
        "session_forecast": True,
        "session_history_summary": True,
        "session_history_delete": True,
        "session_history_bulk_delete": True,
        "hybrid_transport": True,
        "session_artwork": True,
        "session_speech": True,
        "passive_session_surface": True,
        "profile_session_settings": True,
    }


def _contract_versions() -> dict[str, int]:
    """Return additive contract versions clients can feature-detect."""
    return {
        "profile_context": 1,
        "client_contract_fixtures": 1,
        "session_conversation_history": 1,
        "session_history_entries": 2,
        "ask_dj_contextual_dialogue": 1,
        "ask_dj_examples": 1,
        "ask_dj_contextual_exploration": 1,
        "session_mood_music_feedback": 1,
        "moment_track_insight_navigation": 1,
        "session_flow_text_search": 1,
        "active_session_mood": 1,
        "active_session_persona": 1,
        "active_session_presence": 2,
        "session_forecast": 1,
        "hybrid_transport": 1,
        "session_artwork": 1,
        "session_speech": 1,
        "passive_session_surface": 1,
        "session_history_summary": 1,
        "session_history_delete": 1,
        "session_history_bulk_delete": 1,
        "profile_session_settings": SETTINGS_VERSION,
    }
