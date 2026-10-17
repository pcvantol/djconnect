# Configured voice preview v1

Status: directed design; implementation and exact producer fixtures pending.
Existing Core writer and existing Speech/Settings family only. Human selection
was verified in the existing Apple task on17October2026; the consumer proposal
does not itself create a producer capability. No bubble, turn or fake Moment.

## Purpose and authority

An explicit Preview action speaks a short neutral Core-owned sentence using the
confirmed Profile/active-Session voice and gender through the configured HA
Assist TTS provider. It works without an active Session. It never changes a
Profile default, Session, conversation/history revision, presence budget or music
playback. Recording an operation receipt is not a chat/history publication.

Use existing paired transport authority and operation ownership. Proposed operation
`speech/preview` uses the existing version1 operation envelope, UUIDv7 operation
identity and current operation epoch. Its payload is exactly
`{"contract_version":1,"language":"nl"}`; language is one of en/nl/de/fr/es.
No caller text, voice/provider/gender/target override or previous bubble reference.
The server resolves the current effective six-field settings at execution.
Unactivated or migration-ambiguous settings require the existing review; no
implicit activation or guessed defaults merely to produce an example.

The operation is unavailable until its actual capability and exact source pin
are supplied. Apple must not guess an endpoint or replay an unrelated bubble.

## Fixed text and output

| Language | Literal neutral text |
|---|---|
| en | This is a short example of your selected DJ voice. |
| nl | Dit is een kort voorbeeld van je gekozen DJ-stem. |
| de | Dies ist ein kurzes Beispiel deiner gewählten DJ-Stimme. |
| fr | Voici un court exemple de la voix DJ que tu as choisie. |
| es | Este es un breve ejemplo de la voz de DJ que has elegido. |

Speak literally; no LLM, personal facts, retrospective speech or playback claim.
Use neutral vocal delivery for comparing voices, not an invented Moment Mood.
Provider/language/voice availability must be qualified normally. No provider or
system-voice fallback and no global HA configuration changes.

Confirmed output determines targets: client_device prepares private client audio;
ha_speaker dispatches only to the configured physical speaker; both prepares once
and provides separate client/speaker outcomes. text_only returns an explicit deny
with zero synthesis, byte grant and speaker call, including previously prepared
assets. It is not overridden by local autoplay/preview controls. Native local
voice overrides remain client-owned and do not modify this HA-provider example.

## Grant, concurrency and failure

Reuse the bounded private audio owner: original maximum120second expiry,
at most2MiB per asset and existing per-owner/global slot/job limits. A duplicate
operation joins or reads its original result; it cannot refresh expiry or dispatch
the speaker twice. A new deliberate press is a new operation, subject to existing
capacity/backoff. Retain only bounded operation metadata, never raw audio on disk.

Capture owner/pairing/Profile authority, exact settings revision/generation,
selected pipeline/provider/voice configuration and output/speaker target before
synthesis. Check after each await, before semantic result/effect acceptance and
every audio byte read. Reassignment, revoked pairing, text_only, Session lifecycle
change, provider/voice/target change or expiry invalidates pending/old grants.
No broad lock held during provider I/O. No success after cancelled/withdrawn work.

Private client audio uses existing authenticated POST byte access, never a bearer
URL or redirect. Speaker access uses existing short bounded media grants and
transport effect fences. Missing configured speaker never falls back to a different
speaker. Per-target outcomes distinguish ready, queued, unavailable and unknown;
queued/HTTPsuccess is not audible acceptance. After uncertain speaker dispatch,
read the original operation outcome; do not blindly re-execute.

## Consumer contract and acceptance

An optional versioned `voice_preview` result supplies stable preview identity,
literal text/locale, confirmed settings revision, effective provider voice,
original expiry, private client audio reference when allowed, and separate delivery
outcomes. Existing `session_speech` source identity is not forged. Typed errors and
fixed text ship in all five languages. Apple owns Preview/Stop, local playback
coordination, cancellation and UI hiding in text_only; Core owns entitlement.

Before delivery: real owner routes with/without Session, all output modes,
five texts, voice/gender resolution, no chat/Session/playback mutations,
duplicate/cancel/retry, provider/settings/owner/source/target races, original
expiry, both-target partial failure, zero-effects text_only, bounded resources,
independent technical/privacy and UX review, actual wire fixtures and producerpin.
Native, installed and physical audible results remain separate.
