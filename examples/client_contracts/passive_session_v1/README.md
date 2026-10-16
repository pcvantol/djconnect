# Passive Session v1 — provisional producer handoff

Canonical [contract](../../../docs/product/PASSIVE_SESSION_PROJECTION_V1.md).
`request.schema.json` defines exact authorize/read payloads;
`response.schema.json` defines successful active/stale read frames. Disable
returns `success:true, contract_version:1, state:disabled`; malformed requests
400, missing/invalid pairing401, revoked/wrong surface grant403, ended/wrong
Session404, grant capacity409. Existing Profile/source authorization may return
its normal401/403/404/409 error before grant projection. Never cache error data.

`paired-ha.d64b8a7a.http.json` is actual isolated networkless HA transport pinned
to integration source **d64b8a7a9a5262cfe367f0574cab580fc1237765** (171 source
files verified). It includes a real published qualified short contribution,
independent current metadata/cover, normal pairing,20pure reads, wrong purpose/
device/grant, ProfileABA, Mood, music-only, pause, real121secondexpiry and end.
Only external Spotify/knowledge/CDN boundaries are fixtures. Grant IDs in this
public fixture are replaced with `isolated-fixture-grant`; no device token,
account credential or production data is present. Source hashes retain actual
identity. This is an early local pin, not remote/protected delivery.

The subsequent expanded local candidate adds platform capability/version flags,
closed unknown-Mood null fallback and requires surviving current/Flow admission.
Its extended mediarevision/subjectA-vsB/lockedconsent/sourcewithdrawal/end-race
proof is being qualified on its own source hashes. Replace this provisional
pin with the exact reviewed/merged main and official artifact before adoption.

Consumer: request explicit consent in the existing foreground app, keep ordinary
paired credentials in secure app storage, cache **only** `passive_session` and
separately admitted image bytes. Do not share/store `grant_id` or bearer in OS
payloads/deep links; the authenticated app resolves/revalidates them. Validate
binding/generation, ordered delivery_sequence within it and equality revisions;
apply every original field deadline before rendering. Old generation, expiry,
end, source withdrawal or missed update becomes neutral; pause stays active.
Keep contribution/current-music image subjects separate; all five language
alt labels and every source link/Spotify mark survive. No new auto Activity
start after dismissal, alerts, private answers/history, speech or playback.

Core source proof is separate from native rich layouts, foreground/locked/
suspended/terminated/offline modes, ActivityKit/WidgetKit background delivery,
Watch replication and joint hardware acceptance. No Swift or consumer assignment
is authorized by this fixture. Existing SURFACE::APPLE::QUIET-TRANSPORT remains
an independently admitted background package.
