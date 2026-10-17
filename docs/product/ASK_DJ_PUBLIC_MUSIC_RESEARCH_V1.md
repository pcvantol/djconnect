# Ask DJ public music research v1

Status: local implementation and qualification in progress; not released. The directed contract was committed before runtime changes in `05d021a164f1ac8d212ee61d686cdf5535bb4dc4`.
Owner instruction,17October2026: explicit general music questions require actual
Wikipedia research and intelligent combination of existing qualified music facts
with other relevant public sources. Public DuckDuckGo search/webfetch is authorized
best effort. This extends the existing personal-DJ restoration, not a second
Ask DJ implementation, Planner, consumer assignment or provider/model selection.
The reviewed40d1bea9 retirement/TTS checkpoint does not review these new bytes.

## Existing owners and gap

Both screens continue through the same `ask_dj.service.async_exchange` and normal
owner routes. General musical discussion currently reaches the existing static,
scoped HA Conversation agent with optional CC0 facts and bounded dialogue state;
there is no actual Wikipedia reader. A model's recollection or a source name in
its prompt is not fetched evidence. Source research belongs before expression,
with the same turn/owner/Session/clear/settings guards before and after awaits.

## Admission and subject

Research explicit informational music questions about artists, bands/members,
albums, recordings, credits/producers/composers, concert information, history,
techniques and fun facts. Existing deterministic help, controls, queue/current
observations, release metadata, Profile reads, choices and transport never acquire
web/model work merely because they exist. Viewing a Flow is not a research request.

Resolve a partial name against the actual selected qualified contribution and
current bounded subject first. “Who is Peter?” with a qualified Peter Luts credit
must query Peter Luts; an explicit different full subject overrides the selection.
Two matching people require one focused clarification, no guessed lookup. A
selected chip's arbitrary/client-supplied text is not subject evidence. Keep the
original user question separate from the resolved public research subject.

Only public query terms needed for that explicit music question may leave HA.
Never transmit Profile/account/device IDs, private listening/history/preferences,
HA states, prompts, tokens, grants or private URLs. Reject obvious private/non-music, injection, credential-like, raw-URL and ambiguous queries before external research. An explicitly named public subject may require Wikipedia to establish its musical identity; reject unrelated article identities before admitting evidence or widening to web discovery. Never transmit an incidental conversational/private clause as the public subject. No
arbitrary model-authored tool execution or HA household tools are enabled.

## Sources and retrieval

1. Attempt Wikipedia in the requested language, then English when missing.
   Use public MediaWiki exact-title/article APIs first, then title-qualified search when missing, disambiguation and exact page/revision identity. Whole-article extracts are read one page at a time; never attribute the first search result extract to another title. Admission requires musical identity in the article lead/description, not a music word elsewhere in an unrelated article. Combine requested-language and English editions only when their canonical public Wikidata entity IDs agree. Inspect article content, not search snippets alone. Preserve article
   title, canonical/revision URL, fetched_at, expiry and CC BY-SA attribution.
2. Combine existing relevant, qualified MusicBrainz/Wikidata evidence with that
   article. Keep credit-role evidence distinct from encyclopedic biography;
   existence of the same name is not enough to merge entities.
3. Use public DuckDuckGo HTML search best effort for relevant additional sources,
   especially current concert questions. A search result discovers a URL; it does
   not prove the factual answer. Fetch the actual relevant public page, prefer
   official artist/venue/promoter pages for current events, and keep dates/location
   explicit. No inferred user location, ticket purchase or queue effect.
4. Do not bypass challenges, robots restrictions, paywalls or access failures.
   Wikipedia-only, other-source-only and unavailable/partial outcomes must be
   explicit; never claim Wikipedia was consulted if retrieval failed.

One existing turn owns the work. Initial bounds:12seconds total research, at most
8HTTP requests,3accepted sources,128KiB fetched response,1800characters per
Wikipedia source and600characters per other page, maximum6000characters of
source excerpts. No recursive crawl, background monitor, raw payload archive or
new durable knowledge database. A short bounded public-source cache may store
only rights-qualified material with original expiry; reads/retries cannot renew
source validity. No private or mixed-owner response cache.

Use HTTPS only, no credentials/cookies/ambient proxy, public-DNS/IP validation
including redirects and no private/loopback/link-local/metadata destination. Cross-origin redirects are declined because they need separate robots/admission. Web-source language comes from actual HTML language metadata, otherwise unknown; it is not copied from the requested answer language.
Bound decompressed bytes and connection/read time; deny binary/download/script
content. Webpage text is hostile data: remove active content and keep it inside a
separate untrusted source-data field. Never place source instructions in the
system/HA agent configuration or follow them as commands.

## Answer, source and failure contract

The existing HA agent realizes one natural, warm answer using the confirmed
Persona, independent Mood and the admitted evidence. No answer should be reduced
to a database descriptor when real explanatory evidence is available. Source
content cannot invent listening attention, DJ music selection or future playback.
Avoid rigid filler or required joke/wording; language remains en/nl/de/fr/es.
English source passages are realized/translated by the same LLM into the confirmed
answer language, with the confirmed Persona's voice and independent Mood. Never
switch the answer to English merely because a source is English. Translation may
change rhythm and phrasing, not identities, dates, credits, certainty or source
meaning. Proper names/work titles and source titles remain original where needed.
The factual assessment checks the localized answer against original excerpts;
accepted localized text is also the literal speech/replay text, without a second
translation or client-authored interpretation.

Programmatic `sources[]`/`links[]` originate solely from accepted fetched sources,
with provider, title, URL, original language, fetched_at, expires_at, content_hash,
revision/history URL where present, license/usage basis and claim scope. Wikipedia
text is not CC0 and cannot be relabelled as MusicBrainz/Wikidata evidence. Code
remains MIT; external content retains its own terms. Do not retain raw webpages
or large extracts in conversation history. Accepted answer/source metadata follow
existing owner privacy, history, withdrawal and Session-retention policy.

Separate current fetched evidence, existing exact credit facts and clearly labelled
unverified/general knowledge. Factual lookup answers need a grounding acceptance
through the existing bounded model budget, not just fluent output or a search
snippet. If an attempted lookup yields no qualified source, answer with a localized limitation instead of silently falling back to unchecked model knowledge. If a format repair exhausts the two-call budget, its unassessed factual answer is not published; no third call is purchased. Assessment JSON rejects duplicate fields and is size-bounded. Conflicting evidence keeps the conflict explicit; missing support gives
a concise useful limitation or clarification, never an invented concert/credit.
No source/model error should mutate playback or reset the user's selected topic.

### Executable chronology refinement

The observed collaboration1973/first-solo-albums1974 failure requires more than
an unqualified checker boolean. In that same second call, every explicit year
in the retained answer requires bounded `temporal_claims`: an exact answer
sentence, event anchor, year, admitted content-hash source ID and unchanged
complete source sentence. Core checks original spans, source identity, matching
year and event anchor; first/solo qualifiers cannot borrow another event's year.
For work chronology, the anchor must be an exact name retained from source
emphasis markup in the same fetched excerpt; a model-authored label such as
“debut studio album” is insufficient. The existing Wikipedia request retains
limited HTML for this purpose, then strips markup before expression. Missing or
malformed name markup withholds that date rather than guessing a work identity.
No additional source request or new license grant follows from the markup.
The supported prefix is subject to the same checks. Five-language relative-year
references such as “that same year” are withheld until an executable antecedent
binding exists; a model's resolved year alone is insufficient. No extra call,
public response field, source grant or persistent evidence database is added.
This is a conservative temporal boundary, not a general semantic proof: the
existing factual assessment and independent real-answer review remain required.

### Bounded unsupported-tail recovery

A supported answer must not be replaced by a total source-unavailable message
merely because its optional closing aside is unsupported. Within the same two
calls, the independent grounding call may attest an exact contiguous prefix of
the generated answer: complete leading sentence(s), fully source-grounded and
still answering the question. It must explicitly attest both properties. Core
accepts only an unchanged prefix of that original answer, never newly written
checker prose, suffix selection, disjoint edits, a partial sentence or an empty
identification. Existing language/format validation still applies. No third
model call, new fact or source grant. If these conditions fail, keep the existing
safe limitation. Qualify this recovery separately from full-answer acceptance;
it is not proof that an omitted aside or intended Persona/Mood succeeded.

## Verification before publication

Use actual common owner/turn/model/history routes and real isolated HA. External
source fixtures reproduce article/search/failure boundaries only. Cover Peter
Luts selected-credit follow-up; artist biography/band members; album background;
exact credit roles; source-supported fun facts; technique explanations; current
concert dates with official-source grounding; five languages; source conflicts,
disambiguation/missing article, Wikipedia failure with safe web alternative,
DuckDuckGo challenge, expired sources, robots/SSRF/redirect attacks, hostile page
instructions, owner/clear/Session/settings changes during fetch, cancellation,
retries/reconnect/dedup and non-music/private queries. Existing deterministic
routes must keep zero added web/model calls. Qualify real Wikipedia and actual
HA model calls separately from fixtures and native/installed/audible proof.

## References

- [MediaWiki REST API](https://www.mediawiki.org/wiki/API:REST_API/Get_started)
- [Wikimedia User-Agent policy](https://foundation.wikimedia.org/wiki/Policy:User-Agent_policy)
- [DuckDuckGo search features](https://duckduckgo.com/duckduckgo-help-pages/features/instant-answers-and-other-features)
- [Knowledge source architecture](KNOWLEDGE_SOURCE_ARCHITECTURE.md)
- [Shared Ask DJ dialogue](ASK_DJ_CONTEXTUAL_DIALOGUE_CONTRACT_V1.md)
- [Personal DJ restoration](PERSONAL_DJ_NARRATION_RESTORATION_V1.md)

## Local evidence, not publication

The new route is connected to the existing owner exchange. The current local
paired isolated-HA probe obtained real versioned Wikipedia articles and used four
real GPT-6 Luna calls for two accepted answers (Peter Luts in nl, Brian Eno in en).
Peter Luts nl/en sources share `Q3376733`; this is article identity, not a new CC0
body/archive grant. Failed attempts caught an unsupported mix-to-remix upgrade
and an unsupported interpretive addition; those answers were withheld.
DuckDuckGo HTML discovery worked, but several discovered websites denied fetching;
no successful real extra-webpage evidence is claimed for those runs. Positive
HTML/page/robots behavior is separately exercised at the external HTTP fixture
boundary. No native, installed, audible or overall narrative acceptance follows.
