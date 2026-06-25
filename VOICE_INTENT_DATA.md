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
- `Wat is die beuker?`
- `Speel die dikke knaller`
- `What song is playing?`

Behavior:

- Call Spotify backend `status`.
- Do not run Spotify search.
- Do not start or change playback.
- Generate DJ response text/audio from the current track metadata.
- Informal Dutch track words such as `kraker`, `monsterhit`, `vette track`,
  `dikke knaller` and `beuker` can refer to the current/recent track.
- If no track is active or Spotify is unavailable, still generate a friendly DJ
  response.

## Playback Controls

Examples and backend commands:

- `Stop muziek` -> `pause`
- `Start muziek` -> `play`
- `Zet harder` -> `set_volume` with current volume +10
- `Zet zachter` -> `set_volume` with current volume -10
- `Volgende nummer` -> `next`
- `Next` -> `next`
- `Skip` -> `next`
- `Vorig nummer` -> `previous`
- `Ik ga slapen` -> `pause`
- `I'm going to sleep` -> `pause`

Behavior:

- Do not run Spotify search.
- Do not run Assist music intent parsing.
- Use the existing Spotify backend command path.
- Generate DJ response text/audio after the command.
- If Spotify is unavailable, return a friendly DJ response instead of treating
  the phrase as a music search query.
- English one-word controls such as `next` and `skip` remain direct playback
  controls even when the user interface language is Dutch.
- Sleep phrases pause playback directly and do not ask a follow-up question.

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
- `help`: phrases such as `Help`, `Hulp`, `Wat kun je?` and `Welke commando's
  kan ik gebruiken?`. Responses are categorized text-only prompt lists with no
  media cards, images or playback actions.
- `personal_memory_summary`: phrases such as `Wat weet je nu over mij?`,
  `Wat staat er in mijn DJ Memory?` and `What do you know about me?`. Responses
  are text-only summaries from server-side DJ Memory only. They must not fetch
  Spotify profile enrichment, must not use the current playback card, and return
  no images or playback actions. Clients should render only the returned text
  and `djconnect_memory` source metadata.
- `speaker_outputs`: questions such as `Welke speakers zijn er?`, `Wissel van
  speaker` and `Move music to the living room speaker`. Responses contain a
  text list plus `playback_actions[]` with `kind:"output"` and `Activeer` /
  `Actief` button labels when devices are known.
- `retry_previous_request`: phrases such as `Probeer opnieuw`, `Retry` and
  `Try again`. The backend replays the previous retryable playback request from
  server-side Ask DJ history or memory. Clients must not reconstruct the old
  request locally.
- `contextual_play_followup`: short playback follow-ups such as `Speel af`,
  `Speel maar`, `Play it` and `Play that`. Ask DJ resolves these against recent
  chat context, for example a previously discussed track plus artist. It must
  not guess from stale DJ Memory; if the artist is missing, Ask DJ asks `Welke
  artiest bedoel je?` and keeps `action: none`.
- `album_discography`: questions such as `Welke albums hebben Radiohead
  uitgebracht?` and `Welke albums bracht deze artiest uit?`. Responses can
  include a chronological album list, proxied album covers and Play Now actions
  per album.
- `similar_artists`: questions such as `Welke artiesten maken vergelijkbare
  muziek als wat nu speelt?`, using explicit artist, current playback artist or
  recent conversation context.
- `artist_genre_style`: questions such as `Wat voor muziek maakt artiest X?`,
  answered as a natural style/genre description.
- `concert_agenda`: questions such as `Wanneer speelt artiest X in Nederland?`,
  answered with date, location and clickable source links when web agenda data
  is available.
- `next_track_info`: queue questions such as `Wat wordt het volgende nummer?`.
  These read Spotify queue context and can return track, artist, album art and
  a Play Now action, but do not skip automatically.
- `personal_music_profile_analysis`: non-mutating listening-profile questions
  based on DJConnect Memory plus Spotify recently played/top profile data.
- `recently_played_history`: non-mutating recent listening-history questions
  for tracks, albums, artists and playlist contexts, based on Spotify
  recently-played data. Clients should render returned `items[]` as compact
  lists with art/icons and should not invent Play Now controls.
  - Response contract: `intent.category:"informational"`,
    `intent.intent:"recently_played_history"`, `intent.item_type` as one of
    `tracks`, `albums`, `artists` or `playlists`, `action:"none"` and
    `sources[]` containing `spotify_recently_played`.
  - Response shape: top-level `items[]`, mirrored `assistant_message.items[]`
    and proxied `images[]` when art is available. Each item should have a
    display title, subtitle/kind metadata, optional proxied image/thumbnail URL
    and optional played-at label.
  - Client rule: render as a compact vertical list, not as one large media card;
    do not reuse artwork from earlier chat bubbles; do not add Play Now buttons
    unless the backend explicitly returns `playback_actions[]`.
- `personal_music_recommendations`: recommendation requests such as `Speel wat
  anders`. These can return `playback_actions[]` for Play Now buttons but do
  not start playback until the user explicitly taps Play Now.
- `seed_playlist_mix`: requests such as `Stel een playlist samen op basis van
  Radiohead, Massive Attack en Portishead`, `Ik wil een playlist obv tracks
  Reckoner, Teardrop` or `Ik wil een playlist in genre ambient, techno`.
  Responses return one Play Now `track_mix` action with Spotify track URIs. When
  the user taps Play Now, Ask DJ can ask whether the mix should be saved as a
  real Spotify playlist.
- `dj_announcement`: requests for a DJ-style announcement for what is playing or
  the next track.
- `ambient_music_fact`: backend-generated, text-only Ask DJ system messages
  when Spotify playback moves to another artist/album combination. These have
  no user phrase, use `message_kind: system` and can be styled differently by
  clients.
- `idle_suggestion`: backend-generated Ask DJ system message when the client
  opens Ask DJ while Spotify is idle. It can include one personalized Play Now
  action based on DJConnect Memory and Spotify recently played/top profile data.
- `morning_music_suggestion`: greetings such as `Goedemorgen` and
  `Good morning`. Ask DJ answers with a personalized morning suggestion based
  on DJ Memory/listening-time patterns and includes Ja/Nee confirmation actions
  instead of starting playback automatically.
- `confirmation_followup`: server-generated follow-up questions such as
  `Wil je dit nu afspelen?` or `Zal ik je favoriete ochtendplaylist opzetten?`.
  Clients should render the returned `confirmation_actions[]` or
  confirmation-style `playback_actions[]` as Ja/Nee controls and respond with
  `command:"ask_dj_followup_response"`.
- `unknown_or_unsafe`: obvious gibberish, sandbox escape prompts and
  prompt-injection-like text. Ask DJ responds with a short unknown-intent
  fallback such as `Sorry, ik begrijp niet wat je bedoelt.` and performs no
  lookup or playback action.
- `history_retention`: backend-generated Ask DJ system message when the
  server-side history limit is reached. It uses `message_kind: system`,
  `origin: history_retention`, `intent.intent: history_limit_reached` and no
  audio response. Clients should use `history_trimmed_before` metadata to trim
  local cache.

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
