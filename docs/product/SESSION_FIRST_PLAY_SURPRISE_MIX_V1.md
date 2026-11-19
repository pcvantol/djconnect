> Historical version1: fixed-Mood startup semantics. The explicit updated owner

> Historical contract. The owner-selected replacement is [Session For you v1](SESSION_FOR_YOU_V1.md). Original qualification receipts remain historical.
> scope is Music DNA version2 plus playlist navigation, described in
> [SESSION_START_ACTIONS_DNA_V2](SESSION_START_ACTIONS_DNA_V2.md). Original v1
> schema, RAW and protected receipts retain their own scope.

# Session first-play surprise mix v1

This Core-owned action is separate from ordinary recommendations, automatic Mood
feedback, the three Ask DJ suggestions and the existing qualified Help catalogue.
It belongs to the dedicated Apple first-play CTA selected by the owner. It NEVER
creates a Session. Source implementation, protected Source/Final, installation,
actual Spotify access and native playback acceptance remain separate.

## Discover and request

Feature-detect capability `session_first_play_surprise_mix: true` AND contract
version `session_first_play_surprise_mix: 1`. The normal authenticated Session
start/active responses add owner-only `first_play_action`, schema version1:

```json
{"schema_version":1,"id":"session_first_play_surprise_mix","available":true,"label":"Verras me","prompt":"Verras me met een mix voor deze sessie","localizations":{"en":{"label":"Surprise me","prompt":"Surprise me with a mix for this session"},"nl":{"label":"Verras me","prompt":"Verras me met een mix voor deze sessie"},"de":{"label":"Überrasche mich","prompt":"Überrasche mich mit einem Mix für diese Session"},"fr":{"label":"Surprends-moi","prompt":"Surprends-moi avec un mix pour cette session"},"es":{"label":"Sorpréndeme","prompt":"Sorpréndeme con una mezcla para esta sesión"}},"mix_availability":"not_queried","transport":"existing_session_conversation","selection_effect":"genre_starts_exact_mix","automatic_playback":false}
```

This is an illustrative shape, not a live receipt or provider admission.
`available` qualifies making the REQUEST using loaded current owner/Session/source
and never-played evidence. It does NOT say three mixes or a speaker are available.
No provider/model call or warming occurs to render this catalogue. Read the exact
localized prompt from this Core-owned object; do not hardcode an unqualified
suggestion or send the catalogue ID as a command. Existing Help catalogue bytes,
14 qualified NL/EN entries and five-language UI data are unchanged. No new paid
content qualification or unqualified Help publication flag is manufactured.

Only an explicit click sends ONE ordinary authenticated `ask_dj/message` with
that prompt, original client_message_id and `conversation_context.session_id`.
Use the exact active Profile and Session, existing pairing and normal language.
Ordinary standalone “Verras me” recommendations and arbitrary free Send remain
unchanged. No start on view opening, Mood/Presence changes, reconnect or refresh.

## Output then genre selection

The response adds `first_play` (schema1), with state `output`, `genres`,
`unavailable`, `requested` or `uncertain`, a reason and bounded original expiry.
The existing `result_set`/`playback_actions` own opaque result_set_id/action_id.
They are not new reusable grants or an executable catalogue-ID interface.

1. Core checks fresh actual provider playback and inventory. Paused/playing music,
   observed earlier playback, unknown source or recovered/unknown eligibility is
   closed. No active confirmed output returns only normal authorized output
   choices. No search, transfer, playback or model call occurs on the CTA.
2. Explicit selection of an offered speaker uses the normal output effect with
   `play:false`, its original current inventory and original durable once receipt.
   It resumes this ONE request, not another surprise message. Actual selected
   active output must be confirmed before the three genres are prepared. Zero,
   stale, cached, restricted or changed outputs never get guessed alternatives.
3. With a confirmed output, Core requires an actually known-empty queue, not a
   failed or missing queue read. The original current Mood picks three distinct
   possible directions: chill ambient/jazz/soul; groove soul/jazz/funk; energy
   rock/electronic/house; party dance/house/techno. Three bounded parallel ordinary
   Spotify `genre:` track searches return at most8 records each. Only unique,
   canonical, non-local, explicitly market-playable and unrestricted track URIs
   qualify. Each mix needs at least2 tracks; missing choices or identical ordered
   mixes produce truthful unavailable with NO fake genre button.
4. Core returns EXACTLY3 ordinary `track_mix` actions, titled and labelled with
   the original localized genre. Each freezes the actual ordered URI list and
   original output/source/Session/Mood/settings. The normal action renderer sends
   the exact original result_set_id/action_id on a deliberate genre selection.
   `select` or `play` is the single playback grant in THIS advertised flow. There
   is no third “Play Now” tap or client-generated URI list. An explicitly negated
   or informational question never becomes a play grant. Speaker selection never
   becomes autoplay even when a legacy client submits a play-style operation.

These are DJConnect-curated mixes with Spotify tracks, not Spotify-created mixes,
Recommendations endpoint admission, measured Mood fit or numerical music analysis.
Genre search is catalogue direction evidence. No MusicDNA, private taste profile,
model narration or TTS is needed; this flow uses a short localized control reply.
No playlist is silently created and no paused/nonempty queue is deliberately
replaced. Only observed current state can be checked; no cross-endpoint atomic
Spotify queue guarantee or detection of unobserved concurrent provider changes
is claimed.

## Original lifetime and effect ownership

Original Session/Broadcast identity, accepted Mood/settings revisions, Profile,
source/account/provider, privacy/history grant and a maximum60-second UTC AND
monotonic expiry are captured before the first lookup. Every source await and
final dispatch checks them. Output continuation and result-set replacements can
only shorten that ORIGINAL expiry. Client/account changes cannot reacquire it.

Eligibility defaults UNKNOWN. Only successful genuine fresh Session creation
marks READY. Any accepted playing/paused observation closes it BEFORE historical
SQLite awaits; returning to idle, clearing history or copying Runtime values does
not restore it. An explicit genre attempt has one original pending execution
owner; competitors are rejected without cancelling or replacing that owner.
The ordinary durable dialogue effect journal precedes the normal adapter effect.
The last synchronous dispatch fence binds the exact URI order and output, closes
the Session's first-play latch and refuses any second dispatch, including an
adapter retry after401. Lost response/cancel/unknown outcome never resets this
claim or starts a new mix. A later explicit ordinary playback request is separate
and remains available; no automatic new Session or rearm is added.

The existing truthful `action_outcome` distinguishes dispatched from actual
matching first-track/playing/output readback. Success status alone is not audible
acceptance. Uncertain outcomes return no new play buttons and no automatic retry.
Local original source/RAM authorities never appear in public DTOs. Shared owner,
source withdrawal, retained history and transport guards remain mandatory.

## Consumer handoff and qualification

Apple owns the existing PR295 integration. Require this exact implemented version,
the fresh Core action catalogue and actual active never-played Session; keep the
CTA separate from the three suggestion rows, preserve the draft, original request,
output continuation and IDs, and retire it when Core availability closes. Native
must reject stale responses on Profile/Session/Mood/output/foreground changes and
expiry; it must not press an extra Play Now or reconstruct actions from history.

[Schema and actual source-only fixtures](../../examples/client_contracts/session_first_play_v1/)
and [verification](../verification/SESSION_FIRST_PLAY_SURPRISE_MIX_20261102.md)
retain original source/receipt boundaries. A prepared branch/fixture is not an
operative installed pin. Protected Source plus separate original-qualified Final
must precede the protected producer handoff. Actual provider/iPhone/iPad/Mac and
installed acceptance remain explicitly unqualified until individually evidenced.
