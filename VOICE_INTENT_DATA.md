# DJConnect Voice Intent Data

This document describes the canonical spoken voice-intent examples in
`examples/voice_intents.json`.

The JSON file is the data source for website/client examples and cross-repo
voice documentation. Keep it aligned with `music_intent.py`, `processor.py`,
`ask_dj.py`, README examples and any client UI chips that show supported spoken
commands or Ask DJ examples.

## Handling Order

DJConnect handles spoken text after STT in this order:

1. `current_track`
2. `playback_control`
3. `default_playlist`
4. `playlist`
5. `artist_with_track`
6. `album`
7. `track`
8. `artist`

The first two families are not Spotify search intents:

- `current_track` reads current Spotify playback state and generates a DJ
  response without starting playback.
- `playback_control` calls a Spotify backend command directly and then
  generates a DJ response.

Ask DJ examples live in the separate top-level `ask_dj_intents` object. Keep
that separation intact: the `intents` object describes deterministic spoken
music/playback commands, while `ask_dj_intents` describes conversational Ask DJ
requests that may answer with text, links, images, sources or Play Now actions.

## Current Track Questions

Examples:

- `Welk nummer draait er nu?`
- `Welk nummer speelt er nu?`
- `Wat speelt er?`
- `What song is playing?`

Behavior:

- Call Spotify backend `status`.
- Do not run Spotify search.
- Do not start or change playback.
- Generate DJ response text/audio from the current track metadata.
- If no track is active or Spotify is unavailable, still generate a friendly DJ
  response.

## Playback Controls

Examples and backend commands:

- `Stop muziek` -> `pause`
- `Start muziek` -> `play`
- `Zet harder` -> `set_volume` with current volume +10
- `Zet zachter` -> `set_volume` with current volume -10
- `Volgende nummer` -> `next`
- `Vorig nummer` -> `previous`

Behavior:

- Do not run Spotify search.
- Do not run Assist music intent parsing.
- Use the existing Spotify backend command path.
- Generate DJ response text/audio after the command.
- If Spotify is unavailable, return a friendly DJ response instead of treating
  the phrase as a music search query.

## Music Search Families

Search families still map to Spotify search/playback:

- `default_playlist` uses the configured default playlist URI.
- `playlist` searches/starts a playlist.
- `artist_with_track` resolves to a track search with artist context.
- `album` resolves to album search.
- `track` resolves to track search.
- `artist` remains the fallback for generic music requests such as
  `Speel Nirvana`.

Explicit media words win over generic phrasing. For example, `album`,
`plaat`, `nummer`, `liedje`, `track`, `playlist` and `afspeellijst` should
select the matching intent family before generic artist parsing.

## Ask DJ Conversational Examples

Ask DJ requests can come from text chat or app voice/PTT. Informational Ask DJ
requests do not mutate playback; playback/hybrid requests only mutate playback
when the user clearly asks for it.

The website can use `ask_dj_intents` to render example families for:

- `conversation_followup`: short replies such as `Geeft niet`, `Dank je` and
  `Laat maar`. These are answered naturally without rerunning a previous lookup
  or changing playback.
- `album_discography`: questions such as `Welke albums hebben Radiohead
  uitgebracht?` and `Welke albums bracht deze artiest uit?`. Responses can
  include a chronological album list and proxied album covers.
- `similar_artists`: questions such as `Welke artiesten maken vergelijkbare
  muziek als wat nu speelt?`, using explicit artist, current playback artist or
  recent conversation context.
- `artist_genre_style`: questions such as `Wat voor muziek maakt artiest X?`,
  answered as a natural style/genre description.
- `concert_agenda`: questions such as `Wanneer speelt artiest X in Nederland?`,
  answered with date, location and clickable source links when web agenda data
  is available.
- `personal_music_profile_analysis`: non-mutating listening-profile questions
  based on DJConnect Memory plus Spotify recently played/top profile data.
- `personal_music_recommendations`: recommendation requests such as `Speel wat
  anders`. These can return `playback_actions[]` for Play Now buttons but do
  not start playback until the user explicitly taps Play Now.
- `dj_announcement`: requests for a DJ-style announcement for what is playing or
  the next track.
- `ambient_music_fact`: backend-generated, text-only Ask DJ system messages
  when Spotify playback moves to another artist/album combination. These have
  no user phrase, use `message_kind: system` and can be styled differently by
  clients.

For website examples, show Ask DJ families separately from deterministic voice
commands so users understand that some examples are chat/trivia questions rather
than direct Spotify playback commands.

## Maintenance Checklist

When adding or changing voice intent behavior:

- Update `examples/voice_intents.json`.
- Update this document.
- Add or update tests for deterministic parsing or processor behavior.
- Update README/HANDOFF/TODO where user-facing behavior changes.
- Keep website/client docs aligned with this repo's canonical data.
