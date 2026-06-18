# DJConnect Voice Intent Data

This document describes the canonical spoken voice-intent examples in
`examples/voice_intents.json`.

The JSON file is the data source for website/client examples and cross-repo
voice documentation. Keep it aligned with `music_intent.py`, `processor.py`,
README examples and any client UI chips that show supported spoken commands.

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

## Maintenance Checklist

When adding or changing voice intent behavior:

- Update `examples/voice_intents.json`.
- Update this document.
- Add or update tests for deterministic parsing or processor behavior.
- Update README/HANDOFF/TODO where user-facing behavior changes.
- Keep website/client docs aligned with this repo's canonical data.
