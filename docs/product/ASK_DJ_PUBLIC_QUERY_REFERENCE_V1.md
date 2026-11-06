# Ask DJ public query reference V1

## Purpose and authority

A listener can name a public musical subject and then ask for a different detail
without repeating the name. A rejected answer does not make the user's original
name into an unqualified fact. Conversely, rejected generated prose must never
become factual context for the next answer.

Core retains one immutable, RAM-only `PublicQueryReference` per existing bounded
dialogue frame. It contains only the validated subject name, originating request
hash and original owner/thread scope. The name must occur in the current user's
question under the existing full-name/typo check and public-subject safety guard.
The object carries no source passage, answer, credit, role, catalogue result,
provider permission or model-processing grant. It is never restored from cold
history or imported from a client/model DTO.

## Semantic continuation

The normal read interpreter can receive the public name in
`recent_public_query`. The originating hash and private owner/thread identifiers
are not model input. The interpreter may propose exactly:

```json
{"read":"research","reference":"recent","exclude_current":false,"angle":"biography"}
```

`angle` uses the existing bounded exploration angles. This variant has no
`subject` field: Core selects the original name. Extra fields, subject overrides,
unknown angles and effects are rejected. New named subjects, selected credits
and current playback keep their separate existing routes. Free-form wording is
interpreted semantically, not matched against a new list of example questions.

Consumption requires fresh public retrieval, answer generation and independent
full-answer qualification under the existing shared maximum of three agent
calls. A reference supplies no facts. Source and language/style/temporal guards
remain mandatory; no model repair or automatic research retry is added.

## Lifetime, concurrency and erasure

The original pointer and monotonic slot revision are captured in the actual turn
constructor before interpretation awaits. Every reference replacement and clear
advances the revision, including an empty-slot transition. Publication uses a
compare-and-swap against that original pointer **and** revision before topic
reset or operational metadata updates. A late earlier completion cannot overwrite
a newer reference or revive a name through `None → reference → None` or same-name
ABA.

Before interpretation, the captured reference must still be current. Only actual
`research/recent` consumption installs the narrower retained-reference fence at
the common execution entry. That fence checks the original turn snapshot, current
pointer/revision, frame generation/read revision and original owner/thread before
lookup, after awaits and at final delivery. Merely offering a recent reference
does not install a fence that would reject a different, newly named topic after
its own successful completion.

The originating request hash joins the existing shared request-dependency set
before fresh lookup. The same set guards current request withdrawal and is
recorded in ordinary exchange provenance. Erasing that original request clears
its reference even after another turn becomes current. Frame invalidation,
generation changes and archived-context withdrawal clear it; the ordinary
bounded frame lifetime remains unchanged. No new durable memory store or erasure
mechanism is introduced.

## Response scope

Unqualified research fallbacks are Core-authored responses and lose the generated
`model_processing_basis`; their prose is not appended as independently qualified
assistant context. The user's validated name can still be retained separately.
For a request for one interesting fact, the researched-answer instruction asks
for one evidenced factual sentence and one open question, without invented
significance or a second biographical arc. The existing independent assessor
still decides whether the whole actual answer is supported.

No public API operation, client gesture, catalogue publication leaf, playback
grant, deployment or native/provider admission follows from this internal
reference mechanism.

## Frozen selected-performer lookup identity

An explicit partial name may match the single artist label of the original,
server-resolved selected playback entry. Core preserves that same selection and
uses the full label only as a local public-lookup identity, through the existing
public research owner. A cached, withdrawn, expired, combined or otherwise
unidentified playback label does not qualify this expansion. The original entry,
owner/session and lookup expiry remain fenced across source and answer waits; no
current/latest recording is substituted and no deadline is renewed.

The label supplies no biographical fact, role or model-processing permission.
Private recording/edition text and Spotify URIs stay outside model context. Only
independently fetched and qualified public evidence can support an answer. A
different explicitly named subject still detaches from the selected recording.
This internal lookup does not make a partial name into a user-explicit full-name
PublicQueryReference or alter the CC0 model_source admission.
