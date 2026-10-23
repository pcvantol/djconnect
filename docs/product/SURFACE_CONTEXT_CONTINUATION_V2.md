# Original surface context continuation v2

Status: implemented source candidate with current isolated HA evidence; whole-source review and protected delivery pending. No installation, issuer admission or native push GO.

The exact [closed design record](../../examples/client_contracts/surface_push_v2/context-continuation-design-r2.json), SHA256 `f0d8c9b5b87e421f16541cad0e6d321ecfbf0c42c09f72a710f557dd4a526ca6`, has bounded owning Apple client and API relay design acceptance. It supersedes discovery-only v1 context/register use. It changes only the paired Core context and register envelopes; internal API relay and existing revoke/status/read remain v1.

Capture one client UUIDv7 before context. Context and register use that SAME original operation. The server returns an opaque operation-specific `context_handle` and an opaque `purpose_ref` stable only for the SAME original admitted purpose object. Neither is a bearer, enrollment or a substitute owner. V1 context or metadata-only register fails typed409 before any effect; no compatibility fallback bypass exists.

`expires_at_ms` is the original purpose/registration expiry, unchanged across native-token rotations. Separate `context_expires_at_ms` is the original short submit deadline, capped by the purpose expiry, original operation window and first context acquisition plus30seconds. Repeating or recovering a lost context response returns the same original handle/deadlines without renewed budget. Apple pins both deadlines from original PRE-context wall/monotonic samples before the register await. A successful receipt is compared to the original grant expiry, never the short submit deadline or reply-arrival time.

A version2 register response echoes exactly the captured context_handle, operation_id and purpose_ref. Confirmed, unconfirmed and HTTP-error variants are closed in the design record. No unknown result creates a new operation/credential. Different native-token rotation operations can share purpose_ref only when the server validates the SAME original purpose object; matching Session, expiry, opaque hashes or a local UUID is insufficient.

Original source/paired/service/Session/Broadcast guards and the final no-await fence remain mandatory. Finite retained history is never evicted to reopen replay or refund consumed attempts. Expiry, withdrawal, Session end and unload scrub old live context/headers; minimum opaque tombstones remain. The short context guard applies during the registration operation only: a successfully registered row keeps its original purpose authority and expiry after that submit deadline. Widget-only; no Activity external-content right, remote start, signer custody, operator enrollment or provider/native acceptance follows.

The previous source PR1300/protectedf1b711 and separate Final1301/protectede241d23a both have original canonical/durable qualification. This new increment requires its own exact source/tests/actual HA qualification and independent review before operative adoption. All retained work, VibeCast A/B trust and the direct human window through23October16:30Europe/Amsterdam (14:30UTC), with cutoff14:20UTC, are preserved.


The first context acquisition performs the real synchronous paired check before
reserving bounded retained history. Unauthenticated requests cannot exhaust that
history. Once preauthorized, cancellation or a late401/503/OSError retains the
first pre-await wall/monotonic anchors. Purpose withdrawal matches the exact weak
original purpose captured from the service map before the first await; a device
match alone cannot cancel another Session's pending context.

Current verification:3458total regression cases complete successfully, with7
existing skips (3451passes). All13 isolated HA groups pass against the same264
product hashes before and after their runs; both owned containers are removed.
The widget harness additionally sends64unauthenticated context requests with no
retained reservations and interposes late503/OSError only after actual paired
admission, then verifies same-UUID expiry. The three causal review findings are
closed by separate bounded independent reviews; this is not a whole-source GO.

The ten current fixtures are joined to new original RAW receipts; all ten previous
fixture byte sequences remain in the private evidence dossier. The new
[context metadata fixture](../../examples/client_contracts/surface_push_v2/actual-ha-context-continuation.json)
contains decoded-body projections and original receipt/admission/harness hashes.
It omits transient synthetic background credentials and is not an original wire
byte export. Actual HA, HTTP, SQLite and original service fences are exercised;
required operator/issuer ownership, signing and remote API replies are explicitly
synthetic boundaries. Real enrollment, key custody, provider acceptance,
WidgetKit/ActivityKit delivery, installation and user acceptance remain separate.
