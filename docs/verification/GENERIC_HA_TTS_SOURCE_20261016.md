# Generic selected-pipeline HA TTS — local source qualification

Assignment `DJC-CORE-GENERIC-HA-TTS-V1-20261016`, same sole Core writer.
Actual base `8757ecd38a5fe31254a36aba5e0cbe5852edfa7e`;
branch `codex/generic-ha-tts-v1`; [ACK6209937603](https://github.com/pcvantol/djconnect/issues/1101#issuecomment-6209937603).
Contract-first `abd9c7e20647974045be347ec4740d634d1f52ee`;
first material source `b8a13caf4fe26268041414ef35a2cf6ce376212e`.
Predecessor1177/1186 remains closed. No passive projection admission.

## Connected behavior and actual evidence

The [contract](../product/GENERIC_HA_TTS_V1.md) replaces the general Piper-only
gate with HA's supported selected-pipeline/provider interface. An explicit
missing selection does not fall back. No explicit selection uses HA's actual
preferred pipeline, not the first list item. Exact language/voice or advertised
provider default, WAV/MP3, current config/replay fencing and original source
permission remain independent. Old archived text is not new cloud permission:
new accepted messages carry a bounded server-owned processing-basis marker.

[Real transport fixture](../../examples/client_contracts/session_speech/generic-ha-tts-real.http.json)
comes from HA2026.10.0 in one bounded isolated container. All146 integration
Python hashes match the candidate's actual files, zero differences. Actual
OpenAI HA entity and configured `gpt-4o-mini-tts`, default voiceMarin and explicit
current-inventory Cedar/Alloy choices; existing authorized
access entered only via stdin, no installed HA config mount/change. Five public
music questions use the already qualified GPT-6 Luna agent with no tools or
stored responses; five real TTS requests contain only their exact accepted
answers. No catalog payload or private household context. No waveform mock.

Every language follows normal pairing → actual Session start → confirmed
music_only → common Ask DJ acceptance → explicit selected HA pipeline → real
OpenAI TTS → paired private MP3 bytes → cache → Session end → audio404.
The preferred pipeline deliberately differs from the selected one. Read-only
voice-options makes zero syntheses; cached prepare makes zero additional calls;
unsupported gender makes zero additional calls; unauthenticated audio is401.

| Language | Actual MP3 bytes | Prepare/download/cache/deny sequence seconds |
| --- | ---: | ---: |
| en | 109056 | 1.547 |
| nl | 120960 | 1.405 |
| de | 132864 | 1.997 |
| fr | 118656 | 1.544 |
| es | 130560 | 2.157 |

These are measured isolated software timings, not a latency promise or audible
quality score. Five model requests and five syntheses completed. This table describes only the final active-Session fixture.

The previous actual networkless HA/paired/Piper fixture also passes with
published and retained CC0 Moment/private audio, cache, provider inventory and
withdrawal; external music-source/STT/Wyoming-waveform boundaries are explicit
fixtures. It proves local-route preservation, not a human voice or cloud rights.

## Runtime failure feedback and review fixes

The same real HA transport fixture changes the isolated pipeline voice and
observes authorized audioJSON409/no-store. Only the external SDK failure is an
explicit synthetic boundary; Core preparation, safe notice, failed status,
backoff and actual entity-unavailable handling remain real. No extra real TTS
calls were made for failure injection. Five-language unit checks verify safe
instructions; raw synthetic error text never enters the client response.

Two independent P2 findings were fixed before renewed exact review: joined
synthesis completion uses the existing owner-selected still-authorized waiter
when the starting device is revoked; audio409 retains the original contribution
locale even when HA uses another language. Both have connected regression tests.
Failure observations are private/bounded/expiring; reads and cache hits do not
renew health. Text remains usable, no automatic synthesis or question replay.

## Active-session controls and provider inventory

Actual real HA voice-options advertises bounded current supported voices and
owner/Session/device preference scope. Dutch preparation explicitly selects
Cedar and French selects Alloy from the actual OpenAI HA inventory; the other
three use the configured Marin voice. Exact accepted text/selected IDs/private
bytes/cache/end are proved without changing the pipeline default. Connected
unit tests additionally prove removed voice denial/replay409, independent
per-request choices/cache resources, no shared preference/config write,64voice
limit, unknown/oversize/invalid/native-route ID rejection and no inferred gender.
The existing Persona route's two targeted tests also pass; it remains shared
Session CAS state. Native Voice menu/preferences/Persona editing remain open.

Read-only inspection of actual installed HA2026.10 `tts.Voice` confirms only
`voice_id`/`name`. Thus gender is correctly unavailable in this actual adapter;
this does not claim a positive gender selector or provider-specific metadata.
No custom gender catalogue, direct provider lookup or native voice inference.

## Validation and claim limits

Local regression:2025 tests,2018PASS/7existing skips. Owning dialogue/speech119
testsPASS, including configured/default/no-inventory voice, missing pipeline,
locale and provider, malformed WAV/MP3, option change during synthesis/replay,
catalog cloud-denial, retained qualified versus legacy unknown provenance,
capacity/cancellation/backoff, Session-end/Profile ABA and existing privacy.
Unit-only branch-aware coverage: `speech_processor.py`84%,
`speech_feedback.py`89%, combined85%; real HA/Piper execution is
separate evidence, not falsely added to that coverage number. DAG162 tests,
bootstrap/lifecycle/onboarding selected suites70 (63PASS/7existing skips),
schema/generation23views,
projection, Ruff, the normal Medium/High Bandit gate, `git diff --check`, officialhassfest1valid/0invalid.
Three pre-existing Low Bandit findings in untouched exception handlers remain;
no new Medium/High finding. No workflow/runner/consumer source changes or onboarding archive regeneration.

Exact technical/privacy and editorial/UX candidate reviews and protected
publication retain their normal gates. This record claims local source and real
isolated Core/HA-provider qualification. It does not claim main/PR merge,
installed dev/prod update, native Apple adoption/audibility or hardware PASS.
Existing dev/prod still run8757 until normal protected delivery, exact artifact
readback and the separately standing installation instruction are executed.
