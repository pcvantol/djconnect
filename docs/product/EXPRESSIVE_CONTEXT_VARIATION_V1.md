# Expressive context variation v1 — pinned implementation scope

Assignment: `DJC-CORE-EXPRESSIVE-CONTEXT-VARIATION-V1-20261010`.
Admission base: `e0ee7e3ee7265599345ed6c37647623b2a03b27d`.
Branch: `codex/expressive-context-variation-v1`.
This source/type map and form policy precede production implementation.

## Existing source/type map

| Existing family | Current Moment | Qualified anchors and exact source passage | Channels / fallback |
| --- | --- | --- | --- |
| `artist_begin`, Person | Artist | MusicBrainz CC0 artist identity, exact name, birth date and year/month/day precision; normalized `Birth date of {subject}: {date}.` and four existing translations | Existing visual-only owner/shared projection; invalid immutable core uses exact qualified localized copy; missing locale or no fit gives Silence |
| `artist_begin`, Group | Artist | Same existing artist source; formation date, never a birth date; `{subject} formed in {date}.` and translations | Same existing visual-only boundary and fallback |
| `artist_description` | Artist | Wikidata CC0 entity URL; existing localized summary is the subject, existing localized content is the exact descriptor | Only surrounding quotation/phrasing changes; descriptor, summary and attribution remain exact; missing language gives Silence |
| `album_release` | Album | Spotify catalog album URL, exact album name and release-date precision; `Spotify dates this edition of {subject} to {date}.` and translations | Visual-only; always this edition, never original release; malformed core falls back to exact qualified copy |
| Existing selected genre context | Genre | Existing Knowledge-selected Track Insight `analysis.genre` or `track.genres`, exact current track title and artist; `_genre_moment_copy` currently states the genre context of that track | Existing Track Insight channels and attribution remain unchanged; no invented genre definition, sound or influence. Exact existing copy is fallback; no provider extension |

Recording credits, work composers and shared-producer callbacks retain their
current **Track** type. Existing Artist/Album Track Insight narrative remains
verbatim: arbitrary prose is not an immutable anchor suitable for local rewriting.
No new fact key, Moment type, evidence qualification or consumer field is added.

## Pinned form set

All five existing languages (`en`, `nl`, `de`, `fr`, `es`) and four personas
receive two structurally distinct forms for each selected family. Existing
credits/callbacks retain their four forms. The first source-fact form retains
the already qualified persona wording; the second is authored before use.

| Persona | Form A | Form B |
| --- | --- | --- |
| Home | Warm invitation followed by subject/date or exact descriptor; genre framed as track context | Subject-first observation, then source/meaning qualification; genre starts with artist and track |
| Radio | Source-led complete narrative sentence | Date/descriptor-led sentence with explicit subject/source; genre-led framing followed by track and artist |
| Club | Compact subject/date or descriptor statement | Labelled compact source entry with reversed anchor order; genre/artist/track in one restrained sentence |
| Festival | Playful attention cue, without claims of excitement or personal taste | Qualified anchor first, short invitation to notice the credit/context; no invented prior relationship |

Dates remain byte-exact at their original precision. Group/person semantics,
edition qualification, names and exact Wikidata descriptor remain explicit.
Source objects and original attribution are never rewritten. Mood does not
alter facts or persona. Syntax selection uses only the existing bounded
published Runtime style memory; previews and rejected candidates are pure.
The chosen form is checked for final text bounds/read time; exact qualified
copy is the short fallback, otherwise the existing rejection/Silence path.

## Verification boundary

Before/after complete Runtime → Planner → Knowledge → Moment → Flow → Broadcast
sequences use explicitly synthetic source-shaped fixtures, unique qualified
source identities and unchanged production deduplication. All selected
families/personas/languages must publish two forms. Additional focused tests
cover failed previews, bounds, publication-only commits, six-entry memory,
reset, malformed anchors, missing translations and deterministic realization.
Existing lifecycle, credits/callback, consumer and paired-auth tests remain
required. Independent technical/privacy and editorial reviews examine complete
sequences. The unchanged shared renderer is checked in portrait and landscape.
Software proof does not establish installed HA, native Apple or physical Cast/LG
qualification; publication and installation keep their separate exact gates.

## Qualified source candidate

The production content pin is
`eccef27bddaead828c340cd623668b2e55a2de73836a3ae71678e4c65823c962`.
The 100 complete before/after sequences have receipt SHA256
`c832b75ed120338c509cc2958242709316df9d46d9dcc35635ba3841bc9f8469`;
selection, semantic types, source objects and published counts agree.
Consumer examples and their hashes live in
`examples/client_contracts/expressive_context_variation_v1/`.

Validation on this exact production content: 1690 unit tests pass with seven
existing skips; 172 verification-framework tests pass; Ruff and required Bandit
pass. The full unit run used an exact-base test archive plus owned WIP, with all
142 integration files hash-identical, after macOS offloaded-file/SQLite errors
in the initial canonical run. Those initial failures remain separate evidence.
The unchanged paired-live route passes 57 real HA2026.10 receipts, including
ordinary pairing/device authentication, snapshot/update, reconnect, rotation,
fault paths, real 300-second expiry and end. No broad HA-user credential replaces
normal device authentication. Receipt SHA256:
`658bff7d63fc2dacd65e93e3b10acba1c2ab84f5af1aa003a294f37a1a9d36d8`.

Real Core Broadcast through HA HTTPS/WebSocket to the unchanged local and
static renderer passes 400 cases and 800 cards, both orientations and all
families/personas/languages. Links, exact text, geometry/font readability,
transitions, reconnect, empty browser storage and end pass; 160 Dutch images
are retained. Browser receipt SHA256:
`7ed21239c5de88090d3605ac46083d89b508d260e48f682aa5dffffa3dd3d33e`.
Four additional local/static portrait/landscape probes prove expiry and no
expired-card resurrection after reconnect; receipt SHA256:
`eaf00650a410c96f06f2513e1eedc82662fc4bbf4a52ab1541ad73c85c78db5e`.
The isolated native Chrome profile trusts only the test CA for localhost;
normal certificate verification rejects a wrong hostname. System Keychain,
existing browser profiles, Apple labs and HA-dev are untouched. CAF is modeled.

Independent technical/privacy and editorial reviews cover the full source
sequences. Final editorial/UX review visually checked 16 images spanning all
families/personas and both host/orientation paths: GO, no open findings. Initial
generic footers, Genre read-duration expansion and screenshot transition timing
were corrected before the final pins; failed qualified-fact candidate publication
retains the original transaction ordering and consumes no expression choice or
fact source opportunity. Existing Genre opportunity-consumption ordering stays
unchanged.
Earlier disk-full and handoff rate-limit failures are retained without upgrading
their outcomes. Source PR [#1142](https://github.com/pcvantol/djconnect/pull/1142) is protected
merged and exact-main/package qualified as
`c3d061121b449654e340d3e1415fb554bef26c22`. The
[Completion and Finalization](../history/prompts/2026-10-10-expressive-context-variation-finalization.md)
records immutable source-package/qualification evidence; separate Finalization
publication and own cleanup remain gated.
