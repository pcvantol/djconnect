# Core / Apple native Golden admission readback — 20 October 2026

Status: **PENDING_QUALIFIED_PRODUCER_HANDOFF; execute:false**. This records
same-WIP acceptance work, not a new API, reviewed exporter, native run or release.
Owning Core lane #1101; consolidated #1210/#1229/#1230; Apple #158 / PR159.
Apple retains its own source writer. Core has made no Apple-source changes.

## Exact inspected inputs

Apple PR159 source89a12753040ce756eb8a007ea728e7eab5035816:
`Tools/qualification/askdj-golden/README.md`, `golden.py`, `core-catalog.json`.
Catalogue SHA256:
`f54eaffb4d3caa7760a2462e6e4f50943b670409581cbdc04a58c70b00dd1359`.
Its39families/167steps originate from protected Core8b221d07, not the current
unpublished42family WIP. The native approach sends via ordinary AppModel,
reopens Profile history and binds Session timeline/native bubble rendering.
The proposed private producer JSON is still a handoff proposal. A self-declared
QUALIFIED field is not producer provenance. No old lab receipt belongs to a new
native run, and no current research budget was transferred.

## Installed local provider retry readback

Read-only copying of the existing local HA provider's public Python source
shows `AsyncOpenAI` configured with API-key lookup and HA HTTP client, without
an explicit `max_retries` override. No live configuration or key was read.
Installed OpenAI SDK reports version3.10.0 and DEFAULT_MAX_RETRIES=2.
Provider source SHA256:
`3b99888f61fb1711f3e9badd8ebe13e9666708bc932a8342c3fcf2ccd8faa346`.

This establishes retry potential, not a completed provider call or inspection
of every live runtime object. One SDK invocation can make initial+2retry
requests on retryable errors. Further HA agent/tool loops need separate bounds.
Thus a Core agent-invocation ceiling of2 does not establish <=2transport/model
attempts for native test admission. Main's invocation bound is2; selected
research in this unpublished WIP may use3. Neither is an HTTP retry receipt.

The current isolated night harness explicitly constructs AsyncOpenAI with
max_retries=0 and reserves its cumulative budget before each I/O; this native
finding does not increase its36/40 count. No retries were triggered by this
inspection. No live SDK/provider/service setting was modified.

## Reproduced Apple consumer-gate counterexample

Exact `golden.py` and digest-verified catalogue were evaluated offline with
synthetic receipts; no paid or native calls. Canonical step
`ASKDJ-FLOW-open-musical-wish-step-1` has model_policy=one_or_two.

1. Valid synthetic native/provider binding with one completed attempt returns
   PASS_SELECTED_SET, paid_attempts1.
2. Change only native case.model_policy tozero, remove the provider attempt,
   set observed_total_provider_attempts0. The same reconciliation incorrectly
   returns PASS_SELECTED_SET, paid_attempts0.

The policy is read from the native case rather than resolved from the pinned
canonical step. This can hide missing required model evidence. Canonical zero
families must still permit zero; the repair should validate ID-to-policy
consistency and refuse unknown or changed native policy. Full release's
nonzero-total check cannot repair a required individual question admitted with
no model while other questions provide a positive total.

The exact counterexample was delivered to the existing Apple owner, who owns
its repair/review. It is not a Core product patch or a current installed-client
failure. Private receipt: `djc-apple159-policy-counterexample.json`; preserved
under ignored Core night artifacts. Owning Apple source must supply the fix
and its evidence. No closure is inferred from merely reporting it.

## Required producer admission before an actual native run

- Independently verified adapter commit and exact Core installation, native app
  binary/build, same run/Profile/disposable active Session and catalogue pins.
- Qualified family preconditions: some catalogue rows are fixture/provider
  operations, not independent chat strings. Do not run the inventory in a
  personal Session or clear personal history. Exact selected-entry references
  and intended effect/audio scope must be admitted before sends.
- A pre-I/O attempt limit that includes underlying SDK retries and HA loops,
  unknown/unattributed/failed/cancelled attempts, and no automatic retry/resend.
  A declaration based on agent_calls does not qualify that limit. No routine
  production retry changes or new diagnostics endpoint are authorized here.
- Per-case correlation from actual client message to Core turn/answer and
  retained Session entry, with provider attempt/terminal/model/usage evidence
  and complete total reconciliation. Privacy-safe digests alone still need
  independently established origin and exact binding.
- Independent semantic/effect verdicts based on actual correlated outputs and
  backend readback. Text, literal matching or a standalone supported:boolean
  cannot prove queue effect, narrative quality, actual model use or artwork.
- Canonical model policy from the pinned catalogue, strict five-locale export
  when qualified. Existing Dutch questions plus another language field are not
  translated/localized questions. No token or prompt dump in public artifacts.

Native send/render/reopen is separate from tap arbitration, swipes, album Play,
watch UI, pixels, physical audio and installed speech. Compilation and unit
green do not close those. This source readback has not supplied a qualified
producer adapter, private fixture enrollment, actual native/provider run or
acceptance. Those gates remain OPEN in the same WIP.
