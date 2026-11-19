# Installation principal DATA codec V1

Status: closed standalone Core codec, not a registration service or authority.
The implementation is `installation_principal_data.py`. No production runtime,
HTTP handler, startup task or pairing callback imports it in this increment.
Normal protected Source and separate Final qualification remain required.

## Frozen cross-owner input

Private R2 design SHA256
`7b44758c5f7bba76dd3f61b042a776330ee25697523d3bd05248a5697f76db4b`
and47 declarative expectations SHA256
`31ffe4eecb381ec089be0cd724cf524dafe0455e758738cecb191cead724840c`
are retained byte-for-byte under `tests/fixtures/installation_principal`.
Those47 expectations include actual registry/CAS/once/effect cases which this
codec does not execute or qualify. API168 reviewedb6e5360f remains a separate
prepared public-possession DATA source, not an accepted registrar/principal.
No reinterpretation of RegistryData1, af201, Source153 or old issuer wire occurs.

Eleven closed record families cover generation preparation/public receipt,
installation subject, bootstrap context/proof preparation, claimed principal,
device pair join, known-result withdrawal, original admission intent,
original-operation withdrawal and claimed retirement tombstone. A separate
closed operation-status envelope has six exact outcome variants. Matching hashes
and COMMITTED text remain DATA; they establish no actual storage commit or right.

## Before decoding and across joins

Inputs must be primitive ASCII canonical JSON strings. Callers cannot pass a
parsed object, subclass or fabricated decoded record as authority. A bounded
lexical scan precedes generic JSON parsing:32768 outer bytes/depth4/256tokens;
embedded unchanged R1 body separately4096bytes/depth4/128tokens. Strings and
escapes are scanned correctly; unknown/deep/oversized input cannot reach generic
parse first. Duplicate keys, aliases, missing/extra fields, nulls, arrays,
bool-as-counter, fractions, nonfinite values, unsafe integers, UUID-family
fallbacks and noncanonical coordinates are rejected. Errors contain no inputs.

Generic decoding validates exact field types and recomputes the canonical public
JWK pin. Point-on-curve import and signature verification belong to a separate
qualified cryptographic owner; this module supplies neither. All returned maps,
including nested JWK data, are privately owned and immutable. Default repr omits
original strings and values. Output classification is always
`INSTALLATION_PRINCIPAL_DATA_ONLY`; there is no admitted boolean, signer or effect.

Bootstrap joins consume the complete original primitive generation/receipt/
subject/context/proof chain and a separately required expected R1 string. Receipt
hashes, original IDs, install/core, distinct custody and registry epochs, policy,
JWK/pin, context and original transcript must all match. A presented transcript
cannot construct its own expected input. Signing-deadline DATA cannot exceed the
original registration deadline; generation is an independent earlier operation.
The codec does not read a clock or validate actual time authority.

Record digests use exactly
`DJC-PRIVATE-INSTALLATION-RECORD-CANDIDATE-V1` plus one byte0a and canonical record.
Unchanged R1 uses its distinct fixed possession domain plus one0a and body.
The JWK pin is the unprefixed canonical four-member JWK hash. These domains cannot
be interchanged; hashes do not independently authenticate an installation.

## Withdrawal and claimed result separation

Pending-original-operation withdrawal binds an exact acknowledged admission
intent and the full primitive bootstrap chain, original subject/registration/
challenge/nonce and its own withdrawal policy/nonce/operation. It does not require
a future principal-result hash or caller knowledge of the current registry
revision. Known-committed-result withdrawal is a separate closed record kind,
with an exact claimed principal record; no null target, wildcard or fallback.
Withdrawal has its own deadline and may occur after admission expiry. Helpers
relate claimed principal/device/tombstone data to the original chain, without
performing admission, pairing, retirement or storage.

Actual registry code must still atomically reserve the original intent/nonce
and shared withdrawal/terminal capacity before releasing signing preparation,
then fence late ADMIT in the same registry transaction. Unknown outcomes,
withdrawal-before-ADMIT, lost replies and restore cannot be qualified by a codec.
NOT_FOUND does not permit retry; parsing REJECTED_NO_EFFECT does not prove no
reservation/effect occurred. No local revision or epoch becomes source/native
identity. These required owner semantics remain explicit independent gates.

## Executed evidence and preserved scopes

The new isolated actual Home Assistant qualification has six codec/paired-HTTP
cases and reruns all19 existing original Session/source cases on the same278
product hashes. Both role-state GETs remain exact503UNAVAILABLE. The identical
new harness on immutable parent44696 fails at the genuinely absent codec module.
Original receipts, source hashes and the same-harness join are in
[the actual HA derivative](../../examples/client_contracts/installation_principal_data_v1/actual-ha-data-codec.json).
All preceding277 product bytes, original harnesses and historical receipt fixtures
remain unchanged with their prior277-file scope. No old receipt is relabelled278.

Owning API independently compared11 canonical records,6status variants and14
common mutation denials using Node26.13.0 against a captured Core source module;
exact R1 bytes/hashes and original public fixture were checked. Root verified
all original reference input/result hashes. That is bounded public-DATA
compatibility, not a shipped API R2 codec, signature/admission or whole-source GO.
No key generation/signing, provider/model/network or native effect was performed.

The first new HA run omitted the normal required client-type header and failed;
only the new test caller was corrected. The first full suite failed one stale
277-versus278 preflight inventory assertion. These original failures remain
preserved; the cost-free preflight and its boundary tests now admit exactly278
products and still reject neighboring counts before container I/O. No paid
catalogue runner or its original grant is changed or executed.

No new dependencies, public routes, user-facing strings or five-language UI
changes are introduced. Existing EN/NL Help revision2 and free Ask DJ remain.
HA-dev stays on actual installed Source1382/Final1383,277/schema18; this278-file
candidate is not installed. HA production and accepted API production retain
separate scopes. All24 requests+nine gates, bulletin-to-VibeCast audible/style
acceptance, historical atomic queue preservation and Pi recovery remain open in
the existing register. Mac UI remains human-deferred.

Next source: separately qualified custody/once adapters and actual registry
owner integration, using original installation/operator/custody/clock/restore/
withdrawal authority. The selected real provider/private path/backup policy and
complete effect plan are not supplied by this codec. Normal device pairing
should register automatically after the one installation bootstrap; no extra
per-device approval screen is introduced.
