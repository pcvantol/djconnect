# Original historical-source expiry — Core local readback, 20 October 2026

## Trigger and causal evidence

The same Core WIP continues from local895c7f45; no new capability was selected.
Independent read-only review found a P2: historical Session retention was tested
before asynchronous summary/grant/revision reads. Natural time expiry changes no
revision. A selected source could pass its last read and reach model input after
its original retention deadline.

Two new causal regressions fail on the original product, with two failures and
zero errors. The real SQLite/query regression holds the final grant await and
advances an injected wall clock to the original deadline; unchanged policy and
grant must not return the old body. The paired shared-route regression advances
the clock after the last valid source read specifically inside the actual model
dispatch wrapper. Before repair, the external agent-transport fixture receives
Brian Eno's retained composer context. This is proof of a local model-input
fence defect, not an actual provider call or private production-data incident.

The first broad regression exposed only registration/source-pin mismatches:
four existing retention methods needed named Golden bindings, and the local
contextual history fixture contained the preceding source hashes. The existing
SQLite fixture generator was used; all output except source_pins was asserted
unchanged. Delivered retention-bases-v1/v2 fixtures remain untouched. No consumer
pin or adoption is implied. First test development also had a noncausal routing
probe and an initially patched unused import alias; those logs remain retained.

## Product correction

- Shared entry_retained checks the original absolute deadline, with invalid or
  missing metadata refused. Projection uses the same existing UTC time authority.
- Historical _revision_session rechecks Session retention after all awaited
  revision/grant/policy reads. async_open_entry rechecks the entry after its last
  Session read. Existing owner, source, policy and revision fences remain.
- The common Ask DJ guard retains the minimum original dependency deadline.
  After all dependency awaits, the synchronous turn fence checks it before model
  dispatch; the final persistence acceptance fence checks it as well. Rereads
  cannot renew this deadline, and no archived body is held by this new guard.

Independent re-review found a second P2: the new deadline initially did not reach
accepted speech admissions. A third causal test accepted an answer while valid,
held the actual HA speech-adapter's external TTS fixture, advanced to the original
source deadline, then released synthesis. Before the speech fix it returned an
audio asset. The correction attaches the same synchronous validator to shared
turn delivery admissions and preserves its earliest monotonic speech_deadline.
Existing session_speech remembers this admission and cap, then checks it through
resolve/synthesis/audio delivery. No second expiry mechanism or renewed lease.

The final third test checks no audio reference, URL or cached bytes after that
TTS await, one external fixture call and no playback effect. The advertised UTC
expiry is capped to the original deadline within1ms allowed solely for UTC /
monotonic descriptor conversion skew; the actual source guard is tested exactly
at the original deadline with no grace. This is fixture speech/admission proof,
not actual provider, device voice, installed client or audible acceptance.

## Validation and qualification boundary

The three exact regressions pass0.199seconds after the speech correction. The
intermediate282test pass9.049seconds predates that correction and is not the
final frozen-source result. Independent final review and focused/full results
are recorded below after execution. Ruff/diff and Golden schedule remain required.

Golden adds one owned expiry step and one named finding:42families/330steps/
80reports;35Core+29actual-quality gates OPEN. All five retention-policy methods
are explicitly bound and its suite is scheduled before provider work. A local
repair never closes native/installed/end-user acceptance solely from tests.

Modelledger remains byte-identical40reserved/39completed/zero remaining; no key
access or external model/source request. The exact historical text-review packet
is independent of this fix. Actual story quality remains NO_GO, full real
catalogue FAIL, zero paid variants. No push/PR/merge/installation/cleanup,
consumer activation or next-slice admission.


Final independent read-only review: scopedSOURCEGO/no remainingP1P2; the same
three exact tests independentlyPASS0.214s. Assertions are outside provider
callbacks. Earliest original deadline and shared speech admission are preserved.
Final frozen283focusedPASS9.428s; full2825testsPASS/7existing skips83.070s.
Ruff/diff and offline inventoryPASS. Product bytes match the frozen source
manifest, no code/test changes during either execution. Existing ResourceWarning
and slow-task/testdiagnostic output is preserved, not memory/performance proof.
