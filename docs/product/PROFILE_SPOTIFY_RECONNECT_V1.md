# Profile-owned Spotify reconnect from every linked device

Spotify authentication belongs to the selected Profile/account, not to the
client that originally established its HA credential storage. Every currently
linked supported device exposes the same existing Spotify reauthorization
operation. The HA credential-owner entry is an internal storage detail.

The options flow resolves the active device binding generation, Profile,
account, Spotify backend and unique current owner before opening normal PKCE.
It carries public identity fences only, and rechecks them before and after
external URL resolution and token exchange. Missing, ambiguous, disabled or
changed ownership fails closed. An existing owner is updated in place; no
credential is copied into a linked device or another Profile. Orphan recovery
retains its separate explicit fresh-grant admission and cannot elect over an
existing owner. Duplicate callbacks remain consumed once.

An explicit selection of the already selected Spotify backend reuses its
current Profile connection. It does not need credentials on the requesting
client and does not change the Profile, pairing, playback or account. An
explicit reconnect may reconcile only that requester's dead owner reference,
never other devices or another Profile.

Options completion uses the HA options-flow manager. Initial setup grants
remain in their own pending config flow and must not update any unrelated
existing runtime. Existing grants update only their exact current owner.

Scope-observation receipts are persistent metadata, like refresh-token rotation
and status-cache observations. Receipt timestamps must not trigger a full
integration reload. Real backend, client-ID or Profile configuration changes
continue to reload. Requested permissions and all five UI languages remain
unchanged. No live provider, audible playback or native acceptance is inferred
from isolated source tests.

This repair follows the reproduced scope-receipt reload storm and missing
shared-client reconnect action. HA-dev temporarily retains qualified debug
1e990d979d55b5e54f58f3e90f9a65ec03c92516 with the original #1439 overlay;
new main deployment waits for the repaired product to qualify.
