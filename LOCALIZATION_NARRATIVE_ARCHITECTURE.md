# Localization and Narrative Architecture

**Status:** Accepted architecture amendment
**Scope:** DJConnect V4 user-facing realization; no implementation authorization.

## Canonical language model

DJConnect supports exactly the language families `en`, `nl`, `de`, `fr` and
`es`, as defined by `LOCALIZATION_STANDARD.md`. Regional BCP 47 input may be
accepted by native platforms, but is normalized to its supported base family.
Resolution is exact locale, supported base language, effective Session/Profile
language, then `en`; unsupported input is a typed unsupported-locale outcome.
Display labels never determine locale.

Profile owns preferred product, narrative and voice languages. A Session
snapshots one effective narrative locale when it starts; a future approved
language change is a timestamped Session event, never a renderer inference.
Requests may supply one bounded locale override. Renderer locale and Voice
Endpoint locale are presentation inputs, not business-policy owners. Source
and Lyrics language describe supplied material and are never translated by
assumption.

## Realization boundary

Canonical domain state contains semantic facts and structured presentation
intent, not arbitrary user-visible sentences. The Narrative Realization layer
resolves effective locale, fallback, Persona, Mood, safe interpolation,
knowledge grounding, screen/voice form and a realization version. It does not
own Planner decisions, authorization, Runtime state or renderer labels.

Application outcomes use stable semantic codes, localization keys and typed
parameters; diagnostics remain separate. Examples include Session unavailable,
interrupted, authorization failure, history/replay unavailable, migration or
validation failure, unsupported capability and no eligible Voice Satellite.
Static labels belong solely to renderer-native resources: Apple localization,
Windows resources, and Wall Pi QML/Qt translations. HTTP and WebSocket carry
the shared semantic contract plus requested/effective/source locale and
fallback indicator; they never each invent localized text.

## Immutable DJMoments and history

A DJMoment has canonical semantic identity and structured intent. A historical
projection preserves the original effective locale, original realized wording,
safe structured content where approved, presentation/voice metadata,
projection version and narrative-realization version. This records what was
actually presented. A translated or re-realized variant is explicitly derived,
labelled with its locale and version, and never replaces the original.
Original-language replay is default; regenerated voice reads original wording
unless an explicit authorized alternative-language request is supported.
Generated audio, URLs, translation catalogs and raw prompts are never
canonical history.

## Voice, Ask DJ, Lyrics and households

Autonomous room voice uses the effective Session language and a compatible
same-room Satellite/voice; absence returns a typed safe outcome. Replay is
request-authorized, concurrent and temporary. Voice choice is Profile-owned,
Session-snapshotted per language and may be renderer-requested only within
approved bounds.

Ask DJ separately resolves request language and Session/Profile/historical
scope. A private answer, Session action and Planner-approved DJMoment retain
their own language metadata. Lyrics preserve source and quotation language;
the Narrative layer may provide copyright-safe paraphrase or explanation in
the effective locale, never unapproved full translation or reproduction.

One active Profile-owned Session has one deterministic live language. Future
shared Sessions require an explicit shared-language policy; private alternate
language replay cannot alter live room voice.

## Persistence, privacy and governance

Future migrations persist only immutable effective locale, original wording,
approved structured content and realization metadata. They do not persist UI
labels, audio, catalogs, raw prompts or unrestricted Lyrics. Bounded
diagnostics may retain locale/fallback/version categories but not private text.

Every future capability records localization impact in Pre-Flight and
Validation, or explicitly records no user-facing impact. Business logic may
not introduce arbitrary user-visible English strings; all five languages need
testable fallback coverage.

## Delivery order

1. Governance and typed outcome contract.
2. Renderer localization audit and native resources.
3. DJMoment/historical localization alignment and Narrative Realization.
4. Ask DJ and voice language resolution.
5. Lyrics-safe localization, renderer adoption and five-language qualification.

No translation catalog, schema migration, API, client, TTS, Lyrics or Ask DJ
routing change is authorized by this amendment.
