# Persona touch withdrawal and cancellation follow-up — 19 October 2026

State: implemented source candidate; protected delivery and native acceptance OPEN.
Owner-selected Core #1209 / Apple #127. Same sole Core writer, isolated branch
`codex/persona-touch-withdrawal-v2`, base
`93cd18b48656c89fadae62e831a34ddd94d09e10`. Main remains clean, Ask DJ WIP and
Brand PR #1224 preserved. Current-session hostverify exits0 / MATCH with canonical
onboarding4.5.4. No installed service, consumer source or personal history change.

## Demonstrated defects and correction

Apple's producer-gap report correctly identified: cancellation before original
admission was forgotten; and a delivered receipt could not reveal later source
withdrawal. Existing v1 protected history is retained unchanged. A durable
original UUIDv7 journal fence now prevents delayed execution and survives restart
without renewed deadline. Unknown-target fences are device-scoped, preventing
another device from reserving an unadmitted UUID. Existing active cancellation is
terminal; a previously completed receipt remains an outcome only.

The existing paired WebSocket now provides one bounded observation per source
and connection. Actual-send projection follows final authority validation.
Source withdrawal emits a private content-free event; disconnect withdraws the
source/audio grant. A bounded local guard detects provider/settings withdrawal
without another byte fetch. The0.25s cadence is not a physical or network SLA.
Native must observe before display/play and stop/purge on invalidation/loss/expiry.
No new HTTP route, Broadcast content, model call, Flow entry or music command.

## Actual isolated HA proof

[Sanitized request/result fixture](../../examples/client_contracts/persona_touch_reaction_v1/withdrawal-outcomes.json)
pins the full product/harness source hashes and private receipt digest.
Pinned image:
`ghcr.io/home-assistant/home-assistant@sha256:1b64d38f38d922bf9d59336451fd6453e1d614f934456af4ee3d2a51061be3a4`.
Readonly candidate, network none, memory1GiB/CPU2/PID256; no installed config or
credentials mounted. Real paired tokens, TLS HTTP/WS, HA Store/SQLite/Settings3
and HA Wyoming TCP entity are used. External waveform is synthetic; no real
speech/hearing/model claim. Eleven-second rate spacing alone is modelled.

Baseline7operations/1fixture synthesis PASS. Follow-up8operations/5WSframes PASS:
pre-admission cancellation for local_on_device and ha_configured, delayed409/no
synthesis, valid same-deadline observation, Preview supersession after delivery,
unchanged confirmed receipt/no result body, actual Assist pipeline voice change
after downloading RIFF with event withdrawal and later404audio, and socket-close
source disposal. First lab attempt failed because the test passed only a partial
pipeline update; pinned HA requires the full dataclass update. The fixture was
corrected, with no product change to hide this qualification error. The second
run passed; both private logs are retained locally.

## Verification and remaining gates

Owning journal tests additionally cover full global/owner capacity with no
eviction, uncertain saves before/after disk write, restart, delayed success and
completed receipt preservation. Reaction tests cover original real expiry,
provider/source withdrawal without another byte read, another-device isolation,
observer bounds and disconnect. Standard Golden gains two zero-model owner
steps; native gesture/audio quality remains separately open. Final full-suite,
contract, lint and CI results are pinned on the eventual source PR, not invented
in advance. Current product/harness hashes must still match the actual HA run.

An additional causal readback reproduced a cross-device status flaw: another
device using the same unadmitted UUID could hide the initiating device's own
cancellation receipt. Status now prioritizes the same device-scoped fence as
reservation; a regression verifies both the receipt and delayed execution.
Initial full suite2652tests/7skips found one stale inventory expectation165after
the two new Golden steps. The expected count is corrected to167; no scenario
was removed or acceptance weakened. Final full source run2653tests PASS /7 existing skips,77.395s.
38reaction and13journal owner methods pass with identity-only receipts; final
actual isolated HA rerun repeats baseline7operations and follow-up8operations/
5WSframes. All product/harness hashes match its final captured inputs.

No dependency, runtime image, provider policy or package version is changed.
Existing dev tooling pins remain as verified by this session's host bootstrap;
unrelated upgrades are excluded from this bounded behavioral correction.

Independent review, exact-candidate owner authorization, protected merge,
separate Finalization/workspace admission, installed discovery and Apple actual
client rendering/gesture/audio stop acceptance remain OPEN. Touch activation
stays OFF until its qualified chain passes. Core #1225 individual content deletion
remains the selected follow-up; no second implementation starts in parallel.
