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
comes from HA2026.10.0 in one bounded isolated container. All145 integration
Python hashes match the candidate's actual files, zero differences. Actual
OpenAI HA entity and configured `gpt-4o-mini-tts`, voiceMarin; existing authorized
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
| en | 100992 | 1.342 |
| nl | 115968 | 1.320 |
| de | 126720 | 1.426 |
| fr | 90624 | 1.809 |
| es | 115200 | 1.832 |

These are measured isolated software timings, not a latency promise or audible
quality score. Five model requests and five syntheses completed. This table describes only the final active-Session fixture.

The previous actual networkless HA/paired/Piper fixture also passes with
published and retained CC0 Moment/private audio, cache, provider inventory and
withdrawal; external music-source/STT/Wyoming-waveform boundaries are explicit
fixtures. It proves local-route preservation, not a human voice or cloud rights.

## Validation and claim limits

Local regression:2017 tests,2010PASS/7existing skips. Owning dialogue/speech111
testsPASS, including configured/default/no-inventory voice, missing pipeline,
locale and provider, malformed WAV/MP3, option change during synthesis/replay,
catalog cloud-denial, retained qualified versus legacy unknown provenance,
capacity/cancellation/backoff, Session-end/Profile ABA and existing privacy.
Unit-only `speech_processor.py` branch coverage85%; real HA/Piper execution is
separate evidence, not falsely added to that coverage number. DAG162 tests,
bootstrap/lifecycle13, onboarding-package11, schema/generation23views,
projection, Ruff, Bandit, `git diff --check`, officialhassfest1valid/0invalid.
No workflow/runner/consumer source changes or onboarding archive regeneration.

Exact technical/privacy and editorial/UX candidate reviews and protected
publication retain their normal gates. This record claims local source and real
isolated Core/HA-provider qualification. It does not claim main/PR merge,
installed dev/prod update, native Apple adoption/audibility or hardware PASS.
Existing dev/prod still run8757 until normal protected delivery, exact artifact
readback and the separately standing installation instruction are executed.
