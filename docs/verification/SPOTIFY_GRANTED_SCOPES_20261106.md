# Actual Spotify scope receipt source repair — 2026-11-06

The owner requested current DEFAULT token-rights verification and targeted
same-scope PKCE reauthorization. Direct live read-only audit resolved the exact
DEFAULT Profile/provider owner and all11 stored requested scopes; none of the
needed playback/playlist-read requested scopes is missing. No token was printed,
renewed or rotated. The installed callback stores ctx.scopes, not token.scope:
actual provider-granted metadata is UNKNOWN. This is not proof of missing grants
or proof that the Spotify app's independent editorial access is available.

## Source changes

spotify_scope_evidence is a closed bounded metadata receipt from successful
provider token.scope only: version/status/source/observation time/public client-id
digest/validated granted names. Requested remains separate and unchanged. Missing
or malformed scope is unknown; new authorization cannot inherit old evidence.
Same-client refresh without scope preserves a valid original receipt without
renewing its observation time. Wrong-client/malformed/extra-field receipts are
not presented as actual. No raw code/verifier/access/refresh token/response enters
this receipt, diagnostics examples or logs.

Both initial ConfigFlow and repair/options callbacks propagate actual receipt
through their existing custody. Ordinary refresh persists via current enabled
credential-owner ConfigEntry, never a retained/removed/wrong-client entry. Normal
token rotation behavior is preserved. Diagnostics show requested/granted/unknown
and missing requested versus actual names separately; actual missing grants
create existing missing-scopes Repair and a full grant removes it. Unknown legacy
entries preserve compatibility without being declared granted. No UI language,
canonical requested permission, pairing, public capability or source-purpose
policy is expanded by scope metadata.

## Qualification

Ten causal tests initially failed because no receipt/status/storage implementation
existed.14 scope/OAuth tests pass after implementation.347 related OAuth/backend/
config-flow/diagnostics/HTTP/Repairs tests pass; four initial lightweight-entry
failures exposed an options-attribute compatibility edge, corrected defensively
without weakening production owner guards. Lint/diff pass.

All31 actual isolated HA protocol suites pass on unchanged308 product bytes.
The new real HA router/ConfigFlow/ConfigEntry Store/ordinary backend refresh/Repair
proof passes14 cases. It demonstrates full/partial/empty/missing/malformed grants,
Profile/account fencing and duplicate callback, both initial result-consumption
paths, refresh preserving original receipt time, actual Repair creation/removal,
and removed-owner rejection. Only token endpoint and reload are fixtures. No real
OAuth/provider/model/playback or installed mutation occurs in source qualification.
Current receipts are rebound from actual executions, originals preserved.998
Golden references/cases/model policies/locales and execute:false are unchanged.

Original attempts remain: an unnecessary fixture re-enable scheduled unrelated
HA integration setup against a frozen disposable router; it was removed while
legacy disabled-entry proof stays in its original verifier. A refresh fixture
initially reused the obsolete absent-provider alias, so the repair correctly
belonged elsewhere; the final proof uses the actual callback-repaired owner.
No production owner condition was relaxed to pass either fixture.

## Live completion plan and gates

This source repair still requires exact protected CI/new Owner Authorization,
merge, main qualification, HA-dev update preserving1439 and independent runtime
readback. Then execute the already human-authorized normal DEFAULT PKCE flow with
exactly the same11 canonical scopes, handing off only an actual Spotify login/
consent if required. Tokens remain direct HA custody. Read back stored actual
grants and missing names; no playback/playlist mutation tests permission.
Separate documentary Finalization records the actual outcome, not an assumed
grant. App-mode restriction, exact artist/ThisIs resolver and queue semantics
remain separate Ontdek repair/provider acceptance; parked widget4 is excluded.
All five UI languages and Help28 EN/NL /42 pending DE/FR/ES scope are preserved.

Final current proof/native-inventory/ForYou/volume/passive/registration check:
59 tests pass after actual receipt rebinding. Canonical11 requested scope source
bytes are unchanged; all source, harness and fixture hashes are verified. The
current live DEFAULT scope state is still explicitly UNKNOWN until the protected
source is installed and normal same-scope consent completes; no live token action
was smuggled into this source qualification.
