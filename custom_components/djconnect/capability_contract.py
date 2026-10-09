"""Transport-independent platform capability advertisement, never an access grant."""


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
        "session_flow_text_search": True,
    }


def _contract_versions() -> dict[str, int]:
    """Return additive contract versions clients can feature-detect."""
    return {
        "profile_context": 1,
        "client_contract_fixtures": 1,
        "session_conversation_history": 1,
        "session_flow_text_search": 1,
    }
