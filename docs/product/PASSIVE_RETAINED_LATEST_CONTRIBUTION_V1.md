# Passive retained latest DJ contribution — source candidate

Owner requirement: the large iOS/macOS widget lower half shows the current/latest
DJ contribution while space permits. A short current-prominence window is not
that retained-latest display purpose. This increment depends on source #1484 and
its separate finalization; it does not alter that approved head or v1/v2/v3 DTOs.

## Explicit purpose and negotiation proposal

Add projection_version4 only for surface:widget. Explicit enabled/cache consent
and retained_latest:true are required when authorizing this version. Existing
v1/v2/v3 and LiveActivity projection3 are unchanged; Watch remains minimal own
watch_widget1. No DJ contribution is needed for LiveActivity, Dynamic Island or
lockscreen: independently valid now_playing/cover/Mood must survive any shorter
contribution expiry.

V4 keeps the current contribution unchanged and adds independent optional
latest_contribution and latest_contribution_status. It is a source-qualified
retained display of one existing public publication, not current prominence,
not a new Moment, historical replay, TTS, summary, model/provider call or action.
It includes original publication/identity, complete text and original source/
expression attribution, purpose:retained_latest, original retained_expires_at,
bounded cache expires_at and explicit passive_cache/os_snapshot rights only.
The client may clip visible lines but must retain full original attributed copy.

## Original bounded lease proposal

The maximum retained-display lease is1800 seconds from the original publication,
shortened by every original source/copy deadline and any withdrawal. This aligns
with the existing maximum source-fact admission horizon; it does not turn native
Flow retention into a passive grant or relax shorter provider/research expiry.
The1800-second ceiling is a proposed bounded source policy, requiring exact-head
owner review, not an existing installed permission or an indefinite Session lease.

Every emitted snapshot/cache remains at most120 seconds from its already
accepted original observation, further bounded by original retained/source expiry
and own grant. A genuinely new accepted source observation may support a fresh
snapshot containing the same still-valid publication; reads/redraws/cache arrival/
Mood/reconnect cannot renew the publication lease or manufacture observation.
Use original UTC and monotonic clocks; future/expired/uncertain clocks fail closed.

## Selection and barriers

Only the newest selected retained public DJ publication may qualify, with exact
Session/owner/Profile/source/account/pairing fences and continued membership in
the server's admitted active Flow. Revalidate its original full-copy provenance
and per-source passive-purpose rights. No private/history/AskDJ/DNA/client cache
substitution, no title matching and no new catalogue execution.

Pending/withdrawn/deleted content, intentional Silence, music_only, Session end,
pair/owner/Profile/privacy/source/account replacement and disposal withdraw the
purpose. If the newest selected publication is private, overlong, missing rights,
expired or no longer admitted, do not resurrect an older publication to fill space.
Silence is a barrier, never retained prose. Current contribution and current-cover
logic keep their own original deadlines. Retained latest text grants no new cover
or artist-image rights and cannot relabel an older image as current playback.

## Candidate background read

The paired app first obtains the ordinary widget v4 grant and completes its
original WidgetKit registration with background-read and OS-cache consent.
It then posts to `/api/djconnect/v1/push/surface/retained-authorize` with the
paired bearer and exactly `contract_version: 1`, `device_id`, `client_type`,
`session_id`, `registration_id` and the v4 `grant_id`. The response returns a
separate opaque read credential, its registration ID, projection version 4,
and the original registration expiry. Repeating the same request preserves
that credential and expiry.

The widget posts only `contract_version: 1` and `registration_id` to
`/api/djconnect/v1/push/surface/retained-read` with the separate credential.
This reads the original owner-authorized Core projection directly. The
existing background credential remains limited to its original read path.
Both the original registration and the exact v4 grant must still be current.
Rotation, withdrawal, Session end and expiry invalidate this access.
The response contains no image fetch URLs or transferable source grants.

An eligible new publication can cause a content-free WidgetKit reload through
the existing registration and budget. The reload carries neither text nor
the read credential. The widget independently retrieves the contribution from
Home Assistant. The provider can coalesce reloads. Delivery and actual rendering
require separate device proof.

## Required proof and boundaries

Before product admission, demonstrate original publication survives its short
prominence window only with explicit v4 consent, exact1800/source/snapshot dual
clock bounds, no renewal on repeated reads/new Mood, correct genuine fresh
observation, private/Silence/withdrawal/source-expiry barriers and no older fallback.
Actual disposable paired HA proof must show current track/cover remains available
when contribution expires; LiveActivity projection3 and Watch1 stay unchanged.
Original failures and all requalified current receipts are retained separately.

No real provider/model/native/OS action is authorized by this document. Source,
CI, exact owner approval, merge, HA-dev composite installation/runtime readback,
physical large-widget rendering and OS background delivery remain separate.
