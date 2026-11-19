"""Evidence categories only; never a factuality or editorial acceptance oracle."""


def classify_answer(body, *, http_status=200):
    if not isinstance(body, dict):
        return 'unqualified'
    if http_status >= 400 or body.get('error') or body.get('success') is False:
        return 'denied'
    if body.get('knowledge_basis') == 'fetched_public_music_research_v1':
        if not body.get('text') or not body.get('sources'):
            return 'unqualified'
        marker = body.get('research_answer_qualification')
        if marker == 'supported_prefix_v1':
            return 'supported_prefix'
        if marker is None:
            return 'full_answer_supported'
        return 'unqualified'
    if body.get('knowledge_basis') in {'public_research_unqualified', 'public_subject_required'}:
        return 'core_fallback'
    return 'unqualified'
