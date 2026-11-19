# Rich retained contribution / artist-image readback — 20 October 2026

Same consolidated Core WIP aftereb9d95a3. No new product route, protocol,
consumer activation, model call, installation, output dispatch or next slice.
Source tests and actual public-photo source evidence have different boundaries.

## Earlier artist card with another active Session

New owning regression:
`ArtistPhotoOwnerTests.test_paired_old_artist_card_keeps_original_identity_while_another_session_plays`.
It publishes an admitted original artist contribution, ends its Session, closes
and reopens SQLite, starts a different Session/track/artist/source context, then
uses the real paired contract2 media handler to prepare the original entry.

The old artist URI/QID and original source-context arguments remain bound to the
request. The returned actual decoded fixture pixels are historical-only, never
current or active-Flow art. Raw entry/lifecycle/summary storage, current playback
and publication count remain unchanged. There are no new narration calls.
Public photo/Spotify replies and source-authority decisions are external fixtures;
this does not prove real OAuth/account authority or native pixel delivery.

The first assertion compared a read projection whose summary.as_of is refreshed
on each read. That is not a durable mutation. The final regression compares the
actual stored lifecycle and summary rows plus the complete raw entry body, rather
than weakening the no-write requirement. No product fix was needed for this case.
Independent technical review reran the exact test successfully with the qualified
Pillow-bearing interpreter; no P1/P2. Its initial other-interpreter attempt lacked
Pillow and was not called a product or independent PASS.

Golden adds one explicit history/art/current-voice step, also bound to the
existing full active/history art-refresh regression and
`SharedSettingsSpeechTests.test_retained_moment_replay_uses_current_session_voice_then_profile_defaults`.
That speech test preserves original accepted text/Mood, uses the current active
Session's effective voice, falls back to stored Profile voice without a Session,
withdraws older cached audio and honors text-only. External TTS is a fixture;
there is no actual audible result. Scoped image/art/speech/Golden suite:102PASS
in2.495seconds. Current inventory42families/313steps/71reports;
26Core+28real-quality steps remain OPEN.

## Actual public-source photo adapter

A separate isolated pinned-HA test exercised the unchanged public photo adapter
for Q11649. That entity came from the already captured actual Dutch/English
Nirvana Wikipedia lookup, not a guessed name match. The pinned image is
`ghcr.io/home-assistant/home-assistant@sha256:1b64d38f38d922bf9d59336451fd6453e1d614f934456af4ee3d2a51061be3a4`.
The v12 frozen files' photo/artwork/decoder hashes equal current WIP product bytes.

The first empty-HA probe stopped with KeyError during HA client setup and is
retained as NOT_QUALIFIED. A new immutable probe adds ordinary frame/network
initialization in its own disposable HA instance. It keeps product fetching,
host/identity/rights checks and real decoding. No live configuration, credential,
model, server port, speaker or installation was used. Five-request/20second cap;
actual successful probe used four public requests in1.315seconds:
Wikidata exact entity, Commons exact P18 file metadata, structured exact-QID
concert search, then the admitted original Wikimedia image. No second image
retry, name-search substitution or oversized upscaling was introduced.

Receipt: **PASS_SOURCE_ADAPTER_ONLY**. JPEG35642bytes,367×346,
SHA256a8280f5638ccff312f876b12fb6f83da5f34b8c7818ff31d7e103c0e34dc8104.
Public attribution: P.B. Rage from USA, “More Kurt -- too rad”, CC-BY-SA-2.0.
[Original Commons file](https://commons.wikimedia.org/wiki/File:Nirvana_around_1992.jpg),
[license](https://creativecommons.org/licenses/by-sa/2.0/).
File revision0dbf13adb570856c6de6fe2100d13f5589fdc277.

The actual image was visually inspected: a photograph in a stage setting, not
an album cover or logo. Identity remains provider/QID-based, not inferred from
faces. The source metadata live_hint isfalse; do not relabel that metadata as a
verified live classification. The image is small and does not prove high-quality
large-card rendering. No native scale/crop/pixels were observed.

Actual evidence and full attribution are retained under ignored
`artifacts/core-contextual-night-20261020/public-photo-source/`, including both
attempts, scripts, logs, image, metadata and a SHA manifest. The actual public
adapter has no paired private-media owner in this probe: do not combine this
source PASS and fixture owner PASS into a claimed actual end-to-end delivery.
Provider source authority, private image response, native display, current voice
and physical audio still need their separately admitted acceptance.

The model ledger is byte-identical to the40-attempt recovery copy:40/40 remains
exhausted. No model/key work or budget reset accompanied these tests. Same-writer
hostverify MATCH/onboarding4.5.4,481GiBfree/32GiBRAM at pickup. Existing lab
services had restarted before this round; no maintenance/writer run was active
and nothing was interrupted or treated as installed Core readback.

Independent technical review confirms the actual JPEG hash/byte count/decode,
all three product source hashes, script request/deadline bounds and explicit
license. Scoped source-adapter GO only; no additional network request or service
was used by that review. Changed-test Ruff and git diff --check PASS.


## Older contribution exploration with a different active Session — 02:01UTC

New regression:
`ExplorationTests.test_more_on_reopened_older_contribution_uses_original_subject_and_current_style`.
It publishes a normalized composer contribution, ends the original Session,
closes/reopens actual SQLite, then starts a different Session with another
playback and Festival/Party. The ordinary paired Ask DJ handler receives
selected_entry pointing to the older contribution. The top-level context
session_id identifies the current Session; the old source Session appears only
inside selected_entry. This follows the existing current-session-or-null wire
contract, not a new permission for an inactive top-level Session identifier.

The new generic request uses the old complete composer identity and role, not
the current performer. Its new generation receives current Persona/Mood metadata,
uses the existing three-call semantic/research/review path and persists in the
current Flow. The old raw SQL entry/text stays unchanged; current playback and
external effects remain unchanged. Then actual removal of the selected entry
causes404 before another model call: no current-artist fallback or playback.
This is new regression coverage; no product fix was necessary.

External research/model replies are fixtures. The prose intentionally serves
only as an admission/storage fixture, not proof of warmth, Festival/Party voice
or source availability. The actual prior model texts remain untouched. This
does not prove native taps, history UI, pixels, voice settings or audible TTS.

Scoped exploration/Golden/artist-image/Profile-speech modules77PASS in2.652s.
Independent reviewer reran the exact new test plus gates:22PASS/scopedGO/noP1P2.
Ruff/diffPASS. Golden adds an explicit owner-contract step:42families/317steps/
74reports,29Corefindings+29real-qualitystepsOPEN. This step adds positive scope
coverage without inventing an issue or closing an existing function. Full2812
source regression remains the earlier ea91fad7 evidence; no unrun2813full suite
is claimed for this test/documentation-only delta.


## Website-backed older contribution / ordinary speech handler — 03:37UTC

Same WIP after9ef1c92c; no product change or reimplementation of existing voice
selection. The website source's existing publication→shared projection→SQLite
reopen regression now continues through the actual paired speech prepare owner.
With no active Session, an explicit local_on_device manual prepare returns the
exact retained accepted text and complete website/QID/P856 public attribution,
without autoplay, an audio asset or creating a Session. Neither sources nor the
model are called again; the retained text/sources stay unchanged. Removing the
original entry makes the identical request return404 before further source or
model work. This qualifies the new website provider's retained admission path
in one chain, rather than composing separate Wiki/speech fixture results.

External public-page and generation responses are fixtures. Local device speech
admission is not native rendering, actual OS voice selection or an audible
result. The separate existing current-active-Session voice→stored Profile voice
regression remains fixture evidence; no real provider or installed acceptance
is inferred by combining them. The actual HTTP website probe still declined at
robots redirect; no actual website-backed story exists from that probe.

One positive Golden step binds this handler chain and the separate voice test:
42families/326steps/78reports;33Core+29real-qualityOPEN. No new bug, source fix or
closure is claimed. Current hostcheck against canonical GitHub root passes
MATCH/onboarding4.5.4; the first check used the obsolete default Documents root
and its three DRIFT rows are retained as path-mismatched, not remediated.
Model ledger remains40reserved/39completed/zero remaining, no credential/model
I/O. Existing model text/editorialNO_GO and native/art/audio/install gates stay.

Validation: exact extended testPASS0.175s; independent exact testPASS/scopedGO
with noP1/P2. Focused story/Profile-speech/Golden70PASS2.019s, Ruff/diffPASS.
No product bytes changed or broad repeat required; full2821PASS/7skips remains
the earlier9ef1c92c source evidence, not an unrun new full-suite claim.


## Older contribution → ordinary possessive follow-up — 03:52UTC

Same WIP afteraad9a3df. The existing composer/old-Session/current-style test now
accepts the closing invitation with a normal next question, without resending
selected_entry. The real paired route researches the same original composer
and supplies current Festival/Party style despite another current performer.
The second turn uses two generation/review fixture calls, keeps source citations,
changes no playback/effects and leaves the old raw SQL body unchanged. This is
a multi-turn owner contract, not a genuine warm Persona/Mood answer.

Source removal invalidates the old dialogue context. An unselected pronoun after
that reset is a fresh request, so its semantic router may ask for clarification.
The test verifies the actual router projection contains no old subject/text or
selected context, research is never invoked, and the result is a non-generated
Core public_subject_required reply without sources/actions. An explicit
selected_entry to the removed row still returns404 before any model call.
The initial test wrongly demanded404 for the now-unbound pronoun; its two failed
logs are preserved. Independent source inspection identified this as an invalid
expectation, not a product defect or a reason to weaken withdrawal. The final
fixture returns a valid none/none/false plan instead of relying on a swallowed
AssertionError to infer no model routing. No product code change was required.

Golden adds one positive sequence:42families/327steps/78reports;33Core+29actual-
qualityOPEN. Existing real texts/editorialNO_GO, zero remaining model budget,
third-source/semantic novelty/native/voice/audio/install and protected delivery
gates remain unchanged. Fixture prose is not added to actual answer receipts.

Independent review also found a test-P2: privacy assertions inside the router
callback could be swallowed by ordinary agent-error handling. The reviewer
injected Brian Eno into the captured payload only in memory and the initial
test still passed. All privacy assertions now run after the request, outside
that catcher; the callback only captures the real payload and returns a valid
plan. Initial focused211PASS7.509s is retained as pre-correction evidence, not
proof that this negative privacy claim passed. Final independent causal check
and frozen focused result are recorded below. No product leak was demonstrated.

Final scoped independent GO: normal exacttestPASS; the same in-memory subject
contamination now produces1failure/0errors at the outer privacyassertion. The
test-P2 is causally closed without claiming a product fix. Final focused
exploration/shared-dialogue/Golden211PASS7.225s, Ruff/diffPASS. Product unchanged;
no full-suite repeat or new actual/model/native acceptance is inferred.
