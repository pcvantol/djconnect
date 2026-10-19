# Assist conversation agent pairing admission v1

Selected existing Core #1211, the strictly separate predecessor of Core #1212
and Apple #129. Current source candidate; no installed or native acceptance.

Pairing/config-flow admission requires the actual selected Assist pipeline and
an existing available conversation agent with a supported process interface.
Empty selection remains HA’s preferred/default pipeline, resolved by HA’s
`async_get_pipeline(hass, None)`. Explicit selection is exact and never borrows
a different valid pipeline. `async_get_agent` resolves the actual configured
agent; a nonempty engine string alone is insufficient. Native HA agents are
allowed: setup validity does not grant generative/model features or qualify an
LLM. No inference or STT/TTS provider is invoked to validate setup.

STT/TTS engine, language and voice fields may be absent/null, separately or
both. Optional speech does not remove the mandatory pipeline/agent. Both early
user/pair gates use the submitted/current selection; the final initial-setup
voice form validates its actual chosen pipeline; both initial entry-creation
routes revalidate the exact stored choice synchronously after the final Profile
commit await. Direct conversation-agent finish uses the same final guard.
Omitted voice input preserves the earlier explicit choice; empty stays default.
Removal/unavailability yields the existing assist_pipeline_required error with
updated en/nl/de/fr/es instructions. The stored empty/default representation,
identity/pair code/token/profile fields, pairing payload/response and old paired
clients remain unchanged. Existing options/reconfigure and runtime speech paths
are not retroactively gated or migrated by this setup correction.

No provider setup, default-pipeline creation/migration, HA capability booleans,
HTTP schema, voice runtime or Apple UI changes belong to this increment.
Core #1212 must still supply the separately versioned actual HA STT/TTS/speaker
projection; Apple #129 must not infer availability from this pairing acceptance.
Core #1210/Apple #128 catalog+compact Help is independently outstanding.

Qualification exercises four optional-audio combinations, exact and preferred
selection, wrong/missing/removed pipeline, empty/missing/unavailable/unsupported
agent, discovery error, final-form selection revalidation and unchanged existing
config/pair contracts. Synthetic provider/config fixtures are source proofs;
the isolated real HA pipeline/agent/user-form check is distinguished from
actual installed pairing, native UI and speech. Source review, protected checks,
separate Finalization and exact producer handoff precede closure.
