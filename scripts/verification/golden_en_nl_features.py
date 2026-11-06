"""Bounded functional Golden addendum; original paid/5-locale gate is unchanged."""
from __future__ import annotations

LOCALES = ('en', 'nl')
HTTP_CASES = {
    'verify_session_for_you_http': (
        '{locale}_genuine_start_prepares_three_genres_polling_no_provider_or_effects',
        'known_speaker_exact_mix_one_play_confirmation_closes_card',
        'genre_before_speaker_one_flow_bubble_then_same_mix_no_second_genre',
        'duplicate_original_turn_never_starts_twice',
        'authenticated_dismissal_no_effects_polls_remain_hidden',
        'expired_choice_cannot_start_or_transfer_output',
        'old_session_refresh_cannot_rebind_or_replace_new_offer',
    ),
    'verify_music_announcement_http': (
        'twenty_music_only_starts_one_original_text_and_independent_review_each',
        'same_track_occurrence_never_generates_or_publishes_twice',
        'actual_text_only_local_manual_archive_replay_without_generation_or_session_restart',
        'actual_text_only_automatic_archive_speech_denied',
        'original_start_expiry_preserves_only_authorized_manual_replay',
    ),
}
REGRESSIONS = (
    'tests.test_ask_dj_contextual_dialogue.SharedDialogueTest.test_unavailable_provider_after_preparation_returns_instruction_not_old_bytes',
    'tests.test_ask_dj_contextual_dialogue.SharedDialogueTest.test_dutch_unavailable_provider_keeps_text_and_does_not_repeat',
    'tests.test_ask_dj_band_story.BandStoryTests.test_explicit_membership_uses_complete_artist_route',
    'tests.test_ask_dj_band_story.BandStoryTests.test_english_membership_uses_complete_artist_route',
    'tests.test_ask_dj_exploration.ExplorationTests.test_multipart_named_story_uses_semantics_and_actual_question_name',
    'tests.test_ask_dj_contextual_dialogue.SharedDialogueTest.test_english_selected_composer_keeps_role',
    'tests.test_ask_dj_contextual_dialogue.SharedDialogueTest.test_dutch_selected_composer_keeps_role',
    'tests.test_ask_dj_contextual_dialogue.SharedDialogueTest.test_new_topic_detaches_prior_source_dependencies',
    'tests.test_ask_dj_contextual_dialogue.SharedDialogueTest.test_dutch_new_topic_detaches_prior_source_dependencies',
)


def findings(harness, locale, receipt):
    """Require actual execution of every requested scenario, including negative paths."""
    errors = []
    if locale not in LOCALES or harness not in HTTP_CASES:
        return ['unexpected_scope']
    if not isinstance(receipt, dict) or receipt.get('source_unchanged') is not True:
        return ['source_not_stable']
    extension = receipt.get('extension', {})
    if extension.get('language') != locale:
        errors.append('wrong_language')
    outcomes = extension.get('cases', {})
    for name in HTTP_CASES[harness]:
        case = name.format(locale=locale)
        if outcomes.get(case) != 'PASS':
            errors.append('missing_or_failed:' + case)
    counters = ('real_provider_calls', 'model_provider_calls') if 'for_you' in harness else (
        'real_model_provider_calls', 'real_spotify_calls', 'music_or_audio_effects')
    if any(type(extension.get(k)) is not int or extension[k] != 0 for k in counters):
        errors.append('unexpected_external_effect')
    return errors
