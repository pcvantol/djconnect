# Orphaned shared Spotify connection: explicit OAuth repair

A paired client's active Profile can still contain its Spotify account reference
when the original HA provider entry has been removed. That reference alone does
not authorize provider calls. The former shared-client rule hides reauthorization
even in this orphaned state, leaving no normal recovery route.

The existing options action **Reauthorize Spotify** is available for this narrow
case. It uses the active device-to-Profile binding, that Profile's selected active
Spotify backend/account, and its existing app Client ID. It does not reuse a
refresh token from the client, another Profile, a backup or a removed entry.
The user explicitly completes the ordinary Spotify PKCE consent flow. Existing
localized options and OAuth result strings cover all five supported languages.
No new scope or consent is inferred from the old empty account-scopes metadata;
the ordinary requested Spotify permissions are presented for fresh consent.

Admission requires that the original provider entry is absent, not merely
unloaded or disabled. A surviving owner keeps its own reauthorization route.
Another same-Profile provider entry, including a disabled entry, prevents a
second owner. A missing or ambiguous device/Profile/account/app binding also
prevents recovery. The existing persisted device binding generation and exact
Profile/account/backend/app/entry identities are captured before login, checked
after external-URL resolution, and checked again before and after token exchange.
A changed binding or a newly appearing owner cannot accept the pending grant.

Only after successful fresh OAuth and the final synchronous identity check does
HA's existing ConfigEntry manager update the same selected paired entry. It
removes that entry's orphaned owner pointer, records the current Profile/account
identity and fresh grant, removes stale overriding OAuth options, and reloads
that entry. No other Profile, device assignment, history, pairing token, output,
queue or playback changes. The old grant is never copied or treated as proof.
Duplicate callbacks cannot exchange or persist a second grant. A completed
callback is distinct from provider inventory, actual playback and installation.

Source proof: causal unit tests plus
`scripts/verification/verify_spotify_connection_repair_http.py` in isolated real
HA. The latter uses the actual router, current Profile/account/device models,
ConfigEntry manager and disk Store. Token exchange and reload are declared
fixtures: no real OAuth, model, Spotify, device or installed HA-dev mutation.
The real operator login and the selected speaker's provider readback remain
required after normal protected source qualification and delivery.

Owner-selected operational target for the current recovery is the existing
DEFAULT Profile on HA-dev, followed by a bounded test on Speaker in schuur.
That target does not become a general authority to repair other connections or
start playback on other outputs. Shared best-effort Play Now remains a separate
incomplete delivery, with its accepted queue-reliability tradeoff unchanged.

## Source qualification

The frozen repair source passed4585 repository tests (11 existing skips),172
verification-framework tests and26 isolated actual-HA groups. The new callback
harness covers successful disk commit, Profile and account changes during token
exchange, duplicate callbacks and entry disablement. Unit checks additionally
cover a surviving/disabled owner, another owner appearing, changed binding
and reassignment-and-return, stale overriding credentials and the real options
PKCE preparation. All308 integration product files are pinned in current
qualification receipts. Ruff, diff validation and Bandit medium/high checks pass.
The cost-free Help container preflight passes setup/import/ownership/checkpoint
only; it grants no paid-model, native, provider, release or installed acceptance.
The EN/NL Help publication boundary and all five-language data remain unchanged.
