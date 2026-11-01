# Ask DJ recording-production reference V1

Status: implementation under review; not released or installed.

“Tell me about this production” asks about a recording, not automatically about
its performer. The existing read interpreter may propose exactly
`production_story` with `reference:current` or `reference:selected` and
`exclude_current:false`. It supplies no name, URI, credits or playback authority.
An unresolved generic production request asks whether the listener means the
current or selected recording. A subsequent explicit selection such as “Huidig
nummer” retains the original production purpose. A bare current-track selection
without that pending purpose retains the ordinary current-track read.

## Original clarification and concurrency

The RAM-only pending slot contains only type/purpose, original monotonic creation
and 120-second deadline, originating request hash and frame generation/read
revision. It retains no question, recording metadata, facts or effect authority.
The deadline starts at the original read-scope capture before interpretation.
Pointer and monotonic slot revision are captured before awaits. Installation,
consumption and delivery compare both; replacement and empty-slot ABA fail.
Only this turn's own exact consumption can pass its post-completion delivery
check. History erasure, source withdrawal and original context expiry remain
effective after acceptance. A late older completion cannot clear a newer slot.

An unrelated question does not consume this purpose or inherit its originating
request dependency. Its model history excludes that unused originating exchange;
expiry of the unused slot cannot invalidate the unrelated answer. The explicit
current/selected shortcut is bounded and localized in five languages. Free wording
uses the same existing interpreter once, with an availability-only pending flag.
It distinguishes a recording-selection answer (`production_story`) from a new
title/performer question (`recording`/`artist`). Only actual production execution
binds the original pending deadline and dependency before lookup; availability
alone never imposes the old deadline on an unrelated question. No second
interpretation call or blanket title-read-to-production coercion is added.

## Recording identity and independent public evidence

Core resolves the original current/selected identity under existing owner,
source/account and original observation fences. A selected reference never falls
back to current playback. Current playback is checked again after research;
its original 60-second ceiling is not renewed. No local/private URI or display
label becomes a public query or model input.

A strict original Spotify track ID permits one bounded, read-only catalogue GET.
The result must match URI/id/type, be nonlocal and nonrelinked, and identify one
artist. Ambiguous multiartist metadata is unavailable in this version. The
catalogue result supplies lookup identity only. Neither its body nor playback
labels are factual evidence or AI input. Fresh independent public retrieval must
contain an actual marked work title and an explicit artist/work relationship;
mere co-occurrence on an artist page is insufficient. Only the actual public
literals and source excerpts enter normal generation and independent assessment.

Title/artist matching supports public background about that work. It does not
prove an exact master, mix, edition, recording-session credit or sonic claim.
Every actual answer retains existing work/role/source/whole-answer checks and
Persona, Mood, language and model budgets. Missing evidence yields a Core-owned
recording-specific unavailable response, without switching to artist biography,
inventing credits or repeating the generic subject question. Cancellation,
withdrawal and late results cannot publish or grant playback.

This adds no client operation, catalogue publication leaf, playback grant,
deployment or provider/native acceptance. Synthetic transport/model regressions
do not establish factual narrative quality or reproduce a private incident's
HTTP failure. All prior open work remains tracked independently.
