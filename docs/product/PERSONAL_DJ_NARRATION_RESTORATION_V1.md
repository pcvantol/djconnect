# Personal DJ narration restoration v1

Status: In progress; no release, installed, native or audible acceptance.

### Consolidation status

The unqualified media/memory announcement prompt and its independent
current-track model generator are removed in this local repair. Existing
command executors keep their accepted request/playback answer; they cannot
start another proactive model announcer. The existing pipeline function is
reused as the one qualified narration owner with bounded generation/assessment
and original source/owner fences. It accepts legacy command caller shape only
to return that caller's accepted answer, with no model or publication side
effect. Ordinary Ask DJ dialogue remains the shared contextual dialogue owner.
No status-read generation, independent history append or last-Ask-DJ mutation
is restored. Obsolete tests of the removed unrestricted prompt were retired;
qualified-source, exact-fact, guarded transport, publication and non-generation
tests replace that behavior. Test count changes are not added coverage claims.

Literal TTS is a subsequent rendering of the accepted text, not another LLM
rewrite. All spoken Moment types and retained answers use the configured
supported HA provider; Silence never speaks. Provider-default voice IDs/names
may be null. Live/previous-session source, Profile/settings and private audio
expiry still fence preparation and every byte read.

## Complete durable Flow and rolling Session retention

Owner decision, 17 October 2026: every published contribution belongs in its
Session Flow, not just in ephemeral Broadcast state. The owner authorizes bounded
private storage; target platform-wide rolling retention is configurable, with
90 days as the default. This is an addition to the existing restoration, not a
second writer or an authority to rewrite previously published contributions.

Persist publication identity, original timestamp and order at the existing
semantic acceptance transaction. Preserve the accepted text, original style,
attribution and source provenance when its retention basis permits it. No model
regeneration on history read. A source-free publication receipt must remain when
the body is unavailable; represent that state explicitly rather than losing a
place in the Flow. A receipt is not a complete text-retention implementation.

Silence is a typed, source-free Flow event, never a spoken contribution or a
non-Silence summary increment. Deduplicate it under the same Session/Moment
identity. History opt-out, Profile deletion and owner authorization still apply.

Retention applies to a completed/interrupted Session as a unit using its terminal
timestamp. Active Sessions must not lose early entries merely because an entry
has aged. Lowering the global policy must bound reads immediately and use the
existing bounded maintenance/authority fences for deletion, including dependent
Ask DJ references, accepted-event dedup, summaries and speech assets. Increasing
the duration cannot resurrect deleted or withdrawn content. No backfill from
current provider data and no raw provider payload, prompts, tokens or artwork
bytes in Flow entries. Source-content validity is independent of Session age.

Current official Spotify Developer Terms qualify temporary metadata caching
for operation of an application; they do not grant arbitrary retention merely
because a user sets 90 days. Source qualification must therefore distinguish
private Core-authored publication records from retained external content.
Reference: https://developer.spotify.com/terms and
https://developer.spotify.com/documentation/web-api/concepts/api-calls.

Delivery is incomplete until all seven spoken types and Silence survive actual
publication → storage reopen → owner timeline, with exact text for permitted
bodies, explicit unavailable/withdrawn states, no double counts, and measured
cleanup at the configured boundary. Live text, retained text, TTS and native
rendering remain separate acceptance dimensions.

### Versioned private metadata-narration retention basis

`owner_metadata_narration_v1` qualifies the narrow private Session-history use
requested by the owner: text already semantically accepted/published by Core
from normalized Spotify metadata, observed current playback or a previously
qualified exact genre/album relationship. This is temporary functional Session
history, not a provider-content database or a cross-Session knowledge source.
Only the accepted text/summary, immutable Moment identity/type, original
Persona/locale, attribution and exact captured backend/account/provider-entry
binding are retained. Maximum rolling Session cap is90days; a global admin
setting may shorten it. No artwork bytes, audio, raw provider responses, model
prompts, inferred listening attention or reconstructed content.

Admission requires the already qualified source family, original publication
guards and a complete captured source binding. Missing/unknown/unsupported
bases retain only the source-free publication receipt. Reuse the existing
Profile/account/provider-entry validator and revocation signals explicitly for
this new basis. On source withdrawal, strip retained source-derived bodies and
project a stable unavailable receipt, preserving identity/order; invalidate
pending images, speech and dependent context. History reads must fail closed
before asynchronous cleanup, including after account reassignment or restart.
The basis does not authorize model processing or a shared-screen history.
Historical text is a record of that accepted publication, not fresh source
evidence and not a current playback claim. Do not reuse it to open narrative
continuity or reconstruct a live Runtime.

## Speech coverage: every contribution except Silence

The owner's additional requirement applies to every existing spoken DJMoment
type: Track, Artist, Album, Genre, Recommendation, Transition and Session.
The shared owner-only speech capability advertises these types explicitly.
Use the existing accepted immutable text, source attribution and original
validity window for both TTS and replay; never generate a second spoken story.
Silence has no speech, audio segments, replay or autoplay, even when its internal
reason contains text or a caller directly requests its Moment identity.

All types use the same configured HA Assist pipeline/provider qualification,
runtime voice/settings authority, private preparation and replay route. Source
withdrawal, expiry, text-only preference and provider errors remain enforced.
Supporting a type does not override a source's processing rights or make an
unconfigured provider available. Missing/broken configuration must carry the
existing structured provider feedback and user remediation instructions.

Acceptance must separately cover each type's real publication, descriptor,
provider preparation, exact spoken text, attribution, replay and revocation.
The common-boundary regression varies all eight types over a real qualified
publication and verifies seven speech admissions and zero Silence admissions;
this is not a claim of eight generated end-to-end scenarios or audible Apple
acceptance. Native buttons, actual playback and HA speaker delivery require
their own connected qualification.

This additive contract records the owner's 17 October 2026 direction: DJConnect
must feel like a personal DJ across its contributions, with real narrative
variation, warmth, wit, appropriate humour and continuity. LLM enrichment is
explicitly wanted. Fixed sentence rotation is a safe fallback, not the target
experience. Existing completed delivery records remain historical evidence;
they do not qualify this restoration.

## Reuse assessment before implementation

The owner explicitly requires inspection and reuse of the former dynamic DJ
announcement route before building enrichment. Initial source inspection found:

- `pipeline.generate_dj_response_with_assist` already combines HA conversation
  invocation, Mood instructions, compatibility tone, opt-in compact personal
  context, generated-text checks, media-mismatch checks and a local fallback.
- `ask_dj._current_track_generated_announcement` already realizes a short
  current-track announcement through the HA conversation route.
- Both currently decline model processing inside an owner dialogue turn because
  catalog display permission is not a model-processing grant. Do not remove that
  guard to regain expressive output.
- `voice_profiles` is a legacy compatibility owner. Its Mood-to-voice-profile
  mapping must not replace the independent confirmed Session Persona.
- Existing pipeline and processor tests cover style, configured agent selection,
  personal context, mismatch rejection and fallback. Reuse and strengthen those
  contracts; do not replace them with metadata-only Golden assertions.

Before runtime edits, record which existing transport, prompt-building and
validation functions are reusable, which need qualified-input parameters, and
which side effects must remain retired. Consolidate reusable expression work
behind the existing owning pipeline rather than introducing a parallel LLM
announcer. Neither the old unrestricted prompt nor a new facade over two
independent implementations meets this contract. This assessment is source
evidence, not a passed live-model or installed-product qualification.

### Lessons from the existing announcement implementation

Inspected `pipeline.generate_dj_response_with_assist`, its shared conversation
transport and result helpers, the three processor callers, the current-track
announcement helper, `mood`, `voice_profiles`, the default prompt constants,
the persona Markdown resource and their existing pipeline tests.

| Existing mechanism | What to learn / reuse | Required refinement |
| --- | --- | --- |
| Model realizes a short response from resolved context | Allow natural sentence construction rather than selecting a numbered sentence | Pass only independently qualified fields, not the old catalog payload |
| Separate style, Mood and occasional personal-context instructions | Contextual warmth and pace can vary without a joke on every card | Confirmed Persona stays independent; Mood must not select another host identity |
| Compact personal intro is optional | Personal does not require a repetitive greeting or a fixed prefix | Actual opt-in/rights and supported Session evidence; no fabricated familiarity |
| Answer before optional trivia | Give the useful answer first and weave facts into a contribution | This ordering suits a command response; do not impose it on every story/Forecast |
| Existing HA conversation transport and fallback | Reuse the actual invocation owner and error handling | Use its qualified guard path, finite deadline, no fallback to an unqualified agent |
| Missing artist/track and unusable-output rejection | Preserve exact subject binding and functional fallback | Substring presence does not verify dates, roles, relationships or all extra assertions |
| Source-priority prose in the prompt | Prefer grounded detail to invented trivia | A source name in a prompt is not a lookup result or processing permission |
| Output generation metadata | Distinguish generated output from local fallback in qualification receipts | Record bounded reason/timing, not raw prompts, full private context or provider errors |

The previous general helper has both an NL and an English prompt branch; the
current-track helper constructs a Dutch instruction regardless of requested
language. Mood hints also contain Dutch text in the non-NL branch. Five-language
coverage therefore cannot be inherited from these helpers without qualification.

The Markdown persona resource demonstrates the desired warmth, dry humour and
spoken rhythm, but `generate_dj_response_with_assist` actually reads
`DEFAULT_DJ_RESPONSE_PROMPT` from `const`, not that Markdown file. Do not claim
editing the resource changes the live route. Its example also implies newness
without evidence; reuse the tone, not that factual implication.

The old result checks reject empty output, certain internal/device errors and
missing subject labels. They do not independently validate arbitrary trivia.
Existing tests use injected HA service replies: useful regression contracts,
but no evidence of real model quality or natural Persona/Mood differentiation.
The focused standalone pipeline run in the current host test environment hit a
missing `aiohttp` dependency (31 tests, 15 import errors); this is not a new
runtime finding or a passed qualification. Use the established isolated HA
test environment for the connected regression and live-model comparisons.

## One expression owner, one publication boundary

The existing Planner chooses whether and what to contribute. Knowledge qualifies
the evidence. The existing Moment Engine owns realization, including an optional
asynchronous model enrichment stage before semantic acceptance. Flow/Broadcast
receive one immutable accepted result. No second planner, autonomous agent,
client rewriting, post-publication rewrite or independent proactive generator.

Use the configured, scope-qualified HA Conversation route, with no HA device
tools or arbitrary state context. Do not add direct external model APIs to live
routes. The owner's model-call permission does not grant processing rights to
every source. Enrichment is best effort and bounded by the existing opportunity
deadline; it cannot extend that deadline or increase presence budgets.

## Independent inputs

| Input | Effect | Forbidden substitute |
| --- | --- | --- |
| Persona | Recognizable host identity, humour and rhetorical form | A generic opener attached to a clinical fact |
| Mood | Pace, emphasis and emotional shading within that identity | A metadata-only field or a claim about the recording's sound |
| Presence | Existing opportunity selection and shared publication budgets | More model calls or contributions outside the budget |
| Qualified facts | Exact identities, roles, dates, uncertainty and attribution | Invented biography, first-release claims or inferred relationships |
| Permitted Session context | A connection supported by actual published evidence | Claimed listening attention, taste, memories or DJ selection without proof |

Home remains intimate and curious; Radio tells a fluent compact story; Club is
restrained and precise; Festival is playful without permanent hype. Chill is
unhurried, Groove conversational, Energy brisk, Party buoyant. These are host
delivery choices, not measurements of the music or user. Humour is optional and
appropriate to the content; errors, revoked access and silence stay clear and
respectful. Every supported language (`en`, `nl`, `de`, `fr`, `es`) is authored
and reviewed on its own merits.

## Model input and acceptance

Use a **Core-owned symbolic expression brief**. The model receives language,
Persona, Mood, the selected Core family/semantic roles, fixed placeholders and
up to three value-free prior expression frames from the existing six-entry
published-only style memory. Catalog values stay local throughout. No private
history, account/Profile/device identifiers, credentials, artwork or provider
payloads enter a model prompt. The input reference is authored from the Core
schema, never an old rendered sentence with partial redaction.

After three failed editorial pilots, the owner-directed restoration permits a
bounded `qualified_public_context` only for existing eligible MusicBrainz and
Wikidata CC0 facts. It contains the already normalized subject/role/date or
localized descriptor values bound to those exact facts, with processing basis
and provider. A CC0 label on an arbitrary payload is insufficient: ordinary typed
source admission, identity, expiry and owner fences must already succeed. No
new lookup, remembered biography, source payload or listening-profile context.
Spotify-family values remain absent from both model calls. This refinement
supersedes the earlier all-symbolic prototype; that prototype's tests and pilot
scores are not qualification of these new bytes. The model still returns exact
placeholders so local fact binding and independent assessment remain mandatory.

The model freely realizes a bounded frame containing each required placeholder
exactly once. Deterministic validation rejects missing/duplicated/extra slots,
extra digits, links, markup and malformed output. A separate bounded assessment
checks the symbolic frame for supported semantic roles, language, inappropriate
claims and recognizable host delivery. Only then does Core insert the exact
local qualified values without another model pass. Roles, exact date precision,
edition versus original-release qualification and all attribution stay intact.
A bare model verdict is insufficient: local qualification, placeholder and
shape validation, final bounds and publication guards remain mandatory. The
model supplies phrasing, not a new factual assertion or knowledge lookup.

This is no transfer of Spotify model-processing or archival rights. No catalog
value is sent in either realization or assessment, including in history/style
examples. If a family cannot safely be represented with authored symbolic
semantics and exact local bindings, use the existing qualified local realization.
A descriptor remains opaque and unchanged; no model translation of source prose.
Enrichment itself never upgrades visual, speech, audience or retention rights.

Capture owner, Session, playback, Persona/Mood revisions, source validity and
presence state before work; revalidate after enrichment and at the existing
commit. Cancellation, timeout, malformed output, revoked source, stale context
or changed settings must not publish stale text, consume an opportunity, advance
style memory or create a catch-up task. Fall back to a qualified local candidate
if it still fits, otherwise Silence. Cache/dedup cannot renew original validity.

Only successfully published forms update the existing bounded Runtime style
memory. Do not store prompts or model responses as a new archive. Retained Flow
remains subject to original source/retention rights; narrative richness does not
justify archiving prohibited catalog bodies.

## Required ingress inventory

| Family | Existing owner / restoration obligation |
| --- | --- |
| Track credits, Artist, Album, Genre, qualified callbacks | `moment_expression` and `context_expression`: integrate qualified enrichment and meaningful Mood shading; preserve facts and rights |
| Session opening and transitions | Existing Moment Engine: same host identity, observed-context accuracy and opportunity budget |
| Forecast | `forecast_expression`: narrate Planner intent with explicit uncertainty; no queue promise or private Horizon export |
| Ask DJ and Track Insight | Existing common dialogue/analysis routes: resolve actual selected/current subject before realization; source qualification precedes enrichment |
| Lists/help and functional failures | Existing deterministic route: useful complete information and clear labels; no model required merely to add personality |
| Silence, progress and technical heartbeat | No narration or TTS; explicit Silence signal remains a separate client presentation decision |

## Acceptance before delivery

Use identical qualified inputs for before/after comparisons across four Personas,
four Moods and five languages, covering every applicable family. Assert factual
anchors and source identity independently of prose, and review complete output
for recognizable host voice, useful content, natural variation and coherence.
Mood metadata, unequal strings, a shuffled prefix or a joke counter are not
evidence of an improved experience. Include the reported clinical album-date
example and current/selected-subject Ask DJ failures as executable regressions.

Exercise actual HA-qualified model calls as well as no-model, timeout, denied
source, invalid output, cancellation, in-flight music-only, expiry, reconnect,
publication failure and retry. Measure calls, latency and fallback outcomes.
Verify real Runtime/Planner/Knowledge/Moment/Flow/Broadcast and permitted
retained-history projections, then local/static portrait and landscape views.
Exact technical/privacy and editorial/experience reviews must precede protected
delivery. Core, Apple rendering, installed behaviour, TTS synthesis, audible
client/speaker playback and joint product acceptance remain separate claims.

## Initial connected implementation boundary

The current local repair connects the selected qualified-fact path to the
existing `pipeline.generate_dj_response_with_assist` owner. It separates locked
Planner/Knowledge preparation, unlocked HA generation, and guarded locked
persistence/publication. Supported symbolic families include credits, composers,
artist birth/formation/description, exact catalog edition, qualified artist-genre
and already-proven shared-producer/album relationships. The previously approved
local realization remains the failure fallback, with original facts and rights.

Output source values are bound **after** both model calls. The prompt transport
receives symbolic roles plus the narrow qualified public CC0 context above.
Value-free accepted frames are encoded in
the existing bounded `expression_form` memory only after actual publication;
failed previews do not advance it. Reads and reconnects do not trigger enrichment.
Creative presentation is not new factual evidence: owner follow-up model context
uses the original qualified fact excerpt, separately from rendered text.

This is not yet complete coverage of every product ingress. Session openings,
ordinary playback/genre-transition narration, Forecast realization, source-poor
fallback experience and installed/native/audio behaviour still require connected
qualification and any necessary fixes. The existing common dialogue/Track Insight
prompt now also consumes the shared host-identity instructions. No completion,
paid Golden quality PASS or all-family integration is implied by fixture tests.
