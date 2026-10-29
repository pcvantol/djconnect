# Automatic local pairing registration journal

Successful ordinary pairing against a loaded Core entry now schedules the private
registration journal automatically. Status, voice, passive GETs, pending config
flows and startup do not create records. No additional user approval screen is
introduced. The ordinary pair HTTP response is unchanged.

The platform-owned database adds forward migration 16 with a separate store
identity and a hash-keyed local pairing journal. The private key includes the
actual entry/device/client type/token/already-loaded HA installation identity;
it is not the normative signed pair digest and is never exported. Only an opaque
Core store identity and original auth generation are retained as the local ACK.
Raw tokens are not stored in the journal. Existing auth remains authoritative.

The original loaded runtime, entry, data/options objects, auth tuple and negative
fence are captured before scheduling. Admission checks run on the HA loop before
SQL and immediately before commit. The caller checks cancellation and original
currentness after definitive settlement. Repeated pairing retains the existing
record/generation. A token/device/entry change or unload fences the local record
synchronously before scheduling its negative tombstone. Retirement before insertion
also leaves a tombstone, so a late response or token ABA cannot resurrect a row.
A restored journal is not automatically adopted as active authority.

The existing persistence provider offers an opt-in WAL/FULL transaction, retaining
its one write lock through staging, final authorization, commit or rollback and
policy restoration. It verifies actual WAL without changing journal mode, verifies
FULL, then verifies restoration of the prior synchronous policy. An uncertain
restoration poisons subsequent writes until a fresh provider is opened. Existing
ordinary transaction defaults remain NORMAL. A local cap of 4096 retained rows
refuses new records rather than deleting tombstones; this is not an operational
permission/enrollment budget.

This is a private SQLite-acknowledged local registration record. It is not proof
of host VFS power-loss durability, HA ConfigEntry disk acknowledgement, atomicity
between the two storage owners, restore freshness, a qualified push-purpose ACK,
registrar authentication, PoP, signing custody, clock qualification or native
receipt. No pairing epoch, permission lease, selected production policy or real
public principal is invented. The af201 passive A/B contract and both public role
GETs remain unchanged and unavailable. Positive registration still requires those
separate actual gates. The next Core increment is the original-observation status
producer and its owning presentation/UUID/sequence journal.

Qualification uses disposable real SQLite, including reopen, token ABA, early
retirement, pre/post-commit retirement, cancellation during a blocked SQL thread,
non-WAL refusal and silently ignored policy restoration. A separate network-none
HA container invokes the actual PairView and runtime setter with explicitly
synthetic ordinary credentials; all 275 product files are checked before/after.
The thirteen previous HA groups and Help HTTP proof use the same exact product
bytes. These tests perform no model/provider/device actions and do not constitute
HA installation or iPhone push acceptance. Original failed and superseded receipts
are retained separately; the broad suite and independent whole-source review must
pass before protected delivery.
