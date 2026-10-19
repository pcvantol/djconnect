# Device speech availability v1 — Core #1212

Selected separate producer for Apple #129, after source1219 and separate
Finalization1220, main8cb1a467dfc0249fc7b3e79e474841e40249c091. Source WIP,
not a qualified consumer pin or installed/native acceptance. Fresh current-root
hostverify exit0/MATCH with onboarding4.5.4; same sole Core writer. Own previous
source/Finalization checkouts and refs safely cleaned under proven squash patch
equivalence and verified recovery; unrelated erasure/host refs remain preserved.

Audit found existing pair/status transport plus legacy unconditional booleans,
selected-provider voice options, private provider observations, independent HA
speaker policy and supported HA STT metadata interfaces. No new endpoint,
provider/runtime route or secondary settings store is needed.

Add device_speech schema1 only to successful paired/status responses. Resolve
the actual configured explicit or HA preferred pipeline synchronously after the
last transport await, with current runtime/entry/token checks. Missing discovery
or failed authority gives no qualified HA route. Pending config-flow pairing
remains unknown until completed runtime status. Legacy booleans retain their
historical endpoint-implementation meaning for old clients; new consumers use
this versioned snapshot for actual route eligibility, never those booleans.

STT, TTS synthesis for client audio, and HA speaker target are independently
qualified. States are unconfigured, available, unavailable, unsupported, unknown.
Available means currently validated configuration/interface/locale, not a remote
service health probe, completed transcription/synthesis or hearing. STT validates
exact pipeline provider and WAV/PCM16/16kHz/mono metadata without processing.
TTS reuses the actual configured processor and qualified voice/gender inventory;
no inferred gender. Owner-only recent synthesis observations remain separately
scoped and expire; an absent/unresolved owner never borrows observations.
A historical failure never changes valid configuration availability. Its
operational failure/retry deadline remains separate: after the60second backoff,
the same route is retryable while the observation can remain for300seconds.
HA target eligibility is separate from synthesis, text_only output policy and
Apple-local audio. No Apple OS hardware or permission availability is inferred.

Every authorized read recomputes; no cached health, push promise or model/remote
spend. Revisions describe current configuration/provider incarnations. Consumers
refresh on status/reconnect/configuration/language changes and before using an
HA route; runtime errors remain authoritative. Unknown/new version or absence
hides/unqualifies HA routes without erasing saved HA preference or silently
switching/uploading local input. Explicit text_only suppresses both synthesizers
under existing settings3; existing speech prepare/replay and authorization stay
mandatory. Local Apple STT/TTS and permissions remain Apple-owned.

Qualification must cover all four audio configurations, exact/default/removal,
provider/language/voice changes, target independence, final-await withdrawal,
privacy/identity/rebinding, legacy decoding and zero audio/model/provider I/O.
Golden owner bindings, real isolated HA, independent exact reviews and normal
protected source/Finalization gates precede a producer pin. Apple native route
selection, actual speech and full #129 closure remain separately open.
