# Automatic native-surface registration after HA pairing

Status: human-selected product direction, jointly reviewed by owning API and
Apple. This document specifies lifecycle requirements, not a released wire
codec, implementation, credential, deployment or native delivery claim.

## Product flow

Normal successful Home Assistant device pairing automatically starts push
registration. There is no additional HA-owner, Profile-role or push-approval
screen. Required native platform permissions still use the ordinary OS flow.
The earlier proposal for a separate owner-approval action is superseded for
this flow; it must not be reintroduced as an implementation prerequisite.

The selected first presentation is playback status with its last-observed
timestamp. Titles, artwork, progress and a live/current guarantee are excluded.
The OS may retain an old display after a missed update or withdrawal; local
revocation does not promise remote notification delivery or OS erasure.

## A: paired-device enrollment

Start automatically from actual committed pairing, independently of an active
music Session or selected Profile. A successful HTTP pair response is not by
itself that commit: the current pending-flow response can say success with
setup_pending=true while holding pairing_received in RAM. The ordinary pair
handler updates runtime state and calls a synchronous config-entry updater;
that return does not certify durable storage of a new pairing authority.

Core must define the authoritative pairing/credential/entry commit and its
server-owned persistent pairing epoch, including uncertainty and restart.
Bind the real installation, Core instance, entry, device and client. Do not
substitute a client UUID, modified_at, a Profile revision, service boot counter
or a raw-token hash for this authority. A duplicate identical pair request or
lost pair response retains the same original epoch and operation; it must not
create a fresh lease. Actual replacement pairing or device-auth credential
replacement is a different authority transition.

Layer A grants device transport enrollment only. It grants no music status
read, event subscription, Profile access, Session content, native display,
Activity start or Activity update. The ordinary paired-device bearer can
authenticate its existing Core endpoint; it is not an issuer credential and
must not be forwarded or reused as one.

Separate parent transport identity from actual target readiness. A WidgetKit
token may not exist before widget placement. An Activity-update token requires
a genuine Activity. Missing targets remain pending/unavailable; never start an
Activity, invent an Activity ID, reuse app APNs as WidgetKit or select another
token role to manufacture enrollment success.

## B: later Session binding

When the actual authoritative Profile, source, active Session and settings are
available, bind a distinct narrower child to the exact original parent
enrollment ID, generation and pairing epoch. Capture real original witnesses
and revisions. No wildcard/latest Session, routing-hint entitlement, client
authority or synthetic Session may fill the gap. This happens automatically,
without another product approval screen.

The child's original validity is bounded by the parent and its own admitted
purpose, Session, source and settings. Later binding or native-token rotation
does not extend the original parent. Session/source/Profile/settings loss
retires the exact child synchronously before awaiting remote work; it need not
retire a still-valid device-only parent. Unpair, entry removal or replacement
of the HA device-auth credential retires the original parent and all children.
WidgetKit/APNs/Activity target-token rotation is a separate bounded target
operation under the same original parent validity, not that auth transition.
Observed A-to-B-to-A changes never restore an old pending operation.

## Required version, time and recovery decisions

The existing surface context/register v1/v2/v3 and frozen Core R9/API v2 are
Session-scoped. Preserve their exact codecs, rights and original evidence.
Layer A needs a separately versioned purpose/audience/domain and closed DTO;
no null/empty/fake Session or forged old owner-approval hash is permitted.

Before an operative codec is published, owning Core/API/Apple must select:

1. Exact pending-to-committed pairing metadata, authenticated reconnect/read
   route and non-secret epoch correlation, with no client-supplied authority.
2. Three distinct original bounds: short operation/native-proof submission
   cutoff, device-parent validity and narrower Session-child validity.
3. Automatic continuation after a definitively known terminal expiry under
   still-genuine current pairing, separately from an unknown or lost commit.
   A new admitted enrollment must never extend or replay the old one. A finite
   expiry with no continuation policy is insufficient for automatic use.
4. Existing paired-device migration and restart without inventing a historical
   epoch or forcing silent repair/re-pair. Unknown restore/rollback closes.
5. Exact status/error/confirmed outcomes, correlation and target generations.
   Read-only status cannot regenerate a handle, reset an attempt or extend time.
6. Genuine purpose-specific management admission, original clock witnesses,
   and a selected durable-before-effect adapter/commit-uncertainty protocol.

No numerical TTL is selected by this direction record. Do not copy old 30s,
UUID operation windows, legacy eight-hour lifetimes or Source153's fifteen-minute
delegation as a new policy. Actual caps of any selected dependency still apply;
in particular Source153's original owner action and fifteen-minute limit cannot
be bypassed by renaming its route. New A/B authority requires its own admission.

Capture original operations, witnesses and qualified deadlines before scheduling.
Reserve one-use durable state before irreversible effect. Unknown commit, lost
reply or cancellation is not permission for a fresh UUID, native acquisition,
renewed budget or cached-secret recovery. Preserve global counters for the same
actual key across re-pair and management epochs. Missing genuine management,
clock, persistence, native or provider facts leaves positive enrollment closed.

## Qualification and ownership

Core owns committed pairing/epoch, actual scope and automatic server trigger;
API owns its separately authenticated purpose/admission and durable journal;
Apple owns actual SDK role readiness, closed codecs and automatic client work.
Their source, protected delivery, installation, provider and native acceptance
remain separate. Core1368/Final1369 and API159/Final160 are delivered DATA-only
primitives, not proof of the new integrated flow. HAdev is not updated by this
document. No production migration, key action, SDK call or device effect occurs.

Required causal cases include provisional pair success before commit; duplicate
pair after lost reply; device enrollment without Session or native target;
distinct auth-token and target-token rotations; actual source/Session retirement
during commit; expiry versus unknown outcome; re-pair with the same actual key;
and late A-to-B-to-A responses. Original failures and all existing contracts
retain their own scopes. Normal exact reviews, protected source, separate Final
and original qualification are required before any successor delivery claim.
