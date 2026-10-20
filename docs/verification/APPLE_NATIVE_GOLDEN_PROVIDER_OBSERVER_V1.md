# Private Apple Golden provider observer — source prerequisite

**Status:** LOCAL SOURCE / OBSERVED_NOT_QUALIFIED. This is a private verification
adapter, not a production route, native fixture admission or consumer release pin.
It reads no credentials, creates no provider client and installs no HA hook.
No provider attempts in this qualification are paid or reach an external network.

## Concrete problem and implementation

Apple158/PR159 needs real provider transport evidence correlated with the ordinary
paired native app run. `agent_calls`, submission counts and old laboratory reports
cannot supply that evidence. The actual SDK3.10.0 default `max_retries=2` can produce
three HTTP attempts for one invocation. A per-invocation counter cannot cap that.

`tools/verification/native_golden_attempts.py` supplies:

- A mode0600, owner-private journal, exclusive creation, no symlink path and
  flock/flush/fsync reservation **before each actual HTTPX transport dispatch**.
  Failed, cancelled and uncertain reservations remain counted. Reopening never
  recreates/reset the journal or its original budget.
- At most40attempts/run, at most2/turn and at most600seconds, bounded by the
  selected cases' exact question hashes and model policy. `zero` forbids provider
  dispatch. Wrong owner/Profile/Session, case order, question, duplicate client,
  unattributed request or non-admitted provider route fails before I/O.
- One original monotonic deadline plus UTC expiry. The shorter remaining time
  bounds both dispatch and streaming. Same-process reopen preserves the exact
  deadline; a different process instance may read evidence but cannot restart I/O.
  UTC rollback cannot renew the run. Pending attempts survive as uncertain.
- Closed input, persisted-turn/attempt and output schemas. No arbitrary context,
  key, prompt, answer, authorization header, path or exception body is echoed.
  Only hashes, bounded IDs/model metadata, strict token counts and terminal state
  are exported. Unknown fields or altered terminal receipts fail closed.
- A streaming Responses HTTPX wrapper. The supplied transport remains the actual
  I/O boundary, so SDK retries each reserve independently without changing normal
  SDK retry configuration. Completed terminal/model/input/output usage is kept;
  missing usage, broken/incomplete streams and HTTP failures never become success.

The private operator must supply a verified transport and bind the **server-side**
ordinary request while invoking the common service. This source does not replace
that service, configure Assist, monkeypatch live HA or admit any fixture itself.
Only HTTPS `api.openai.com/v1/responses`, streaming POST without URL credentials,
query or fragment is covered. Unsupported calls are refused, not silently counted
as observed. Other provider clients/transports require independently proven coverage.

## Actual server/answer binding

The observer accepts original response plus independent reopened assistant and
Session repository entry reads, never a native report used as its own producer
truth. It checks owner, Session, client message, assistant message/text and the
conversation-DJ entry's message/turn relation before recording hashes.

Important consumer meaning: Apple's `server_turn_sha256` hashes
**`assistant_message.id`**, not `conversation.turn_id`. The latter is a different
server identifier. `answer_sha256` hashes the actual accepted assistant text;
`session_entry_sha256` hashes the actual matching conversation-DJ entry ID.
Both native and producer must observe those same original values in the same run.
The observer itself does not establish that the operator supplied authentic reads.

## Fail-closed export and still missing native admission

Export is forcibly `OBSERVED_NOT_QUALIFIED`, semantic/effects `NOT_REVIEWED`,
`provider_coverage: BOUND_CLIENT_ONLY_NOT_ALL_INSTALLED_PROVIDERS`,
`unattributed_provider_attempts: null`, native/installed `NOT_RUN` and release
`NOT_GRANTED`. Neither an input label nor successful offline fixture can upgrade
this. The output is **not** Apple's required qualified producer export yet.

Before a genuine native run/export can be admitted, Core still must qualify:

1. Exact reviewed/protected producer and installed source readback, with all
   relevant configured provider clients/transport paths actually covered.
2. The actual disposable Profile/active Session, authorized paired ordinary app,
   exact binary/build and Core installation receipt, selected complete-family
   preconditions and admitted effects/output. No personal history reset or fixture
   creation is performed by this helper.
3. A real provider budget bound to that runtime run and its cumulative authority.
   This helper's per-run ceiling is not a new spending grant or transfer of Core's
   current300attempt grant to Apple. No fresh run/UUID resets a human cumulative cap.
4. Actual server/history/entry/answer receipts and actual provider terminal/token
   receipts from that same native run, followed by independent semantic/effect and
   narrative review. An earlier isolated Core answer cannot be attached to it.
5. Native hosted-runner execution, history reopening and real bubble rendering.
   Compilation/source fixtures do not establish that the current host can launch
   the ordinary hosted app. Native gestures, local/HA speech and physical audio
   remain separately qualified.

The current Apple catalogue remains protected Core8b221d07,39families/167steps,
consumer SHA256 `f54eaffb4d3caa7760a2462e6e4f50943b670409581cbdc04a58c70b00dd1359`.
This source does not silently substitute the larger local Core WIP catalogue,
translate Dutch questions by changing a locale, infer missing special fixtures,
or override unsupported prose model policies in the consumer adapter.

## Executed qualification and review

Nine local journal tests cover concurrent reservation, failed attempts/total cap,
reopen/no reset, wrong owner/question/replay, zero-model policy, expiry/cap mutation,
secret-field rejection, original assistant/entry binding, private file rules,
strict usage and persisted tamper rejection. An independent review found twoP2s
(open admission keys and UTC-only lifetime); both were repaired and the source
herreview returned scopedGO. This is no installed/native/semantic approval.

Four tests run the **actual OpenAI3.10.0 SDK and HTTPX0.28.1** in the already
pinned HA image, with `--network none` and explicit `MockTransport` responses:
first503thencompletion counts both actual transport attempts and preserves the
failure; default SDK would issue3 attempts while the guard permits only2;
unbound/unsupported calls perform zero transport I/O; UTC rollback during an
incomplete stream still times out at the original monotonic deadline and closes
it. No real provider, live key, API usage or native app is involved.

The commands are:

```sh
python3 -m unittest tests.test_native_golden_attempts
python3 scripts/verification/verify_native_golden_attempt_transport.py
```

The second command needs the SDK dependencies. It was run inside
`ghcr.io/home-assistant/home-assistant@sha256:1b64d38f38d922bf9d59336451fd6453e1d614f934456af4ee3d2a51061be3a4`
with network disabled, bounded memory/CPU/PIDs, all capabilities dropped,
no-new-privileges and a read-only source mount. Failed/intermediate and final
logs are kept separately under the current Core evidence root.

Exact tested source checkpoint: `4a307e6dd4e7e5a1e214000d9bea53900a54c811`.
The final isolated Linux run executes all9journal plus4actual-SDK regressions:
**13PASS,1.047s**, network disabled. The full ordinary suite on that checkpoint
is **2839testsPASS,7existing skips,72.313s**. Ruff/diffchecksPASS. These observations
add **zero actual external provider attempts**; the cumulative Core grant ledger
stays16reserved/16completed/284remaining. No native fixture was admitted.
