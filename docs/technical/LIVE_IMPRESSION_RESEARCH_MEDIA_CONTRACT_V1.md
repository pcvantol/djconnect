# Live-impressie producer-consumer contract v1

Assignment: DJC-LIVE-IMPRESSION-V1-20261108. Current implementation increment: 19 November 2026. Canonical product design: [Live-impressie](../product/LIVE_IMPRESSION_EXPERIENCE_V1.md).

## Existing owners and additive contract

Reuse the existing authenticated Session Moment, native admission, persistence/history, public research safe fetch, HA conversation model, and private Session image registry. Artist-photo v2 stays unchanged: event discovery is a separate content input, not a relaxation of P18 artist-photo identity.

Moment type and knowledge-intent type: `live_impression`. Optional `live_impression` object:
```json
{"schema_version":1,"event":{"event_id":"stable-public-event-id","artist":"original artist","date":"2020-01-01","date_precision":"day","venue":"original venue","city":"original city","relationship":"same_artist"},"photos":[{"photo_id":"stable-original-photo-id","revision":"original-byte-sha256","caption":"original caption","alt_text":{"nl":"...","en":"...","de":"...","fr":"...","es":"..."},"width":1600,"height":1000,"source_url":"https://original-public-photo-page","author":"creator","credit":"visible credit","license":"CC-BY-SA-4.0","license_url":"https://creativecommons.org/licenses/by-sa/4.0/"}]}
```

Moment title/summary/content are respectively title, lead and complete accepted story. The v1 producer currently emits one hero; the bounded envelope supports at most three original photos. No extra gallery is required for the first complete native delivery. Date precision is day/month/year. Relationship is same_artist/song_performed/exact_recording; the first implementation admits same_artist only, never infers recording relation. Sources use existing source references and source records.

History uses archive_basis `public_live_impression_v1`, retained original title/summary/text, source records and the same live_impression object. Session/Profile deletion and original entry retention govern the content independently from live playback-source expiry. Permanent signed URLs, research HTML, prompts and photo bytes are not stored in history.

## Managed image delivery

The existing authenticated POST `/api/djconnect/v1/session/media/prepare` accepts contract_version 3 with targets `{moment_id,photo_id}` or `{entry_id,photo_id}`. IDs resolve only from original published/retained owner content. Response `session_media[]` has schema_version 3, the original target and photo_id, and the existing artwork envelope. Its subject is `{provider:"public_research",type:"event_photo",uri:photo_id}`; role is live_impression; usage_basis is licensed_event_image_owner_display. URL is the existing exact managed session image path, requires_device_auth true, cache_policy no-store, crop_allowed false, upscale_allowed false. media_revision equals the original photo revision. Original photo identity/revision must match after download; no photo replacement. Outer revision is projection equality, not an identity grant.

Transport lease is at most 300 seconds and never extends retained-content authority. Explicit preparation resolves the original photo only; renderer/history reads never research or generate. Transient image failures preserve narrative; actual source withdrawal is separate. No image authorization inferred from Spotify source context.

## Native admission

Qualified Live-impressie has requires_spotify_attribution false and source_expires_at null (independent retained public research). Current display has the original finite presentation deadline. Active flow requires the original live Session and published Moment identity. History is read-only, owner-authorized and retained. Shared VibeCast requires independent shared rights and is not admitted by the private consumer contract.

## Validation boundaries

LI01–LI20 in the canonical design control acceptance. Fixtures/unit checks, real public-source discovery, live HA model, native screenshot/a11y, audible TTS and physical display evidence remain separate. Implementation does not claim provider configuration, publication, signing, installation or deployment.

## Current component inventory

| Existing owner | Disposition | Local delta |
|---|---|---|
| Knowledge/Planner/Presence and intra-track opportunity | REUSE | No new opportunity or scheduling loop. Qualified artist-story opportunity can yield Live-impressie. |
| public_artist_narration / pipeline HA model | ADAPT | Existing agent and guard; shared 12-request operation budget, at most two model calls, no second writer after rejected rich output. |
| public_research.PublicFetch | REUSE | Public resolver, HTTPS/robots/redirect/byte/request limits and no ambient credentials. Literal event search hint is not identity evidence. |
| artist_photo original licensed-file validator | REUSE | Validate bounded image-search results in batches of three. Existing artist-photo P18 policy remains unchanged. |
| live_impression_research | NEW bounded input adapter | Commons image discovery + original caption/date/rights + actual public web pages + existing independent claim assessment. No new research service. |
| DJMoment / native admission / existing SQLite history | ADAPT | Same immutable IDs and immediate semantic persistence, independent public research archive basis. |
| Session image registry / authenticated media GET | ADAPT | Version3 original-photo target; transient bytes move to existing bounded registry and are absent from Moment/history. |
| Ask DJ selected subject and original-text speech | ADAPT | Event follows the original Moment after track changes; original row grants/retention fence current and historical replay. |
| Private→shared projector | GAP / independent acceptance | Owner-only first source does not confer VibeCast rights or shared-screen acceptance. |

No broad dependency/tool upgrades accompany this bounded source change; existing locked product dependencies are reused. JPEG/PNG are at most 2MiB, 4096 per side and16million decoded pixels, no upscaling. DateTimeOriginal or actual caption dates the event; media upload time never does.

Software contract fixtures are generated from actual Runtime/SQLite/media/speech serializers with synthetic source/model input by `tests/test_live_impression.py`. They do not constitute real web research, live HA model or installed/native acceptance. Real source probe evidence currently verifies discovery and original JPEG bytes for one historical Muse concert; the complete web-story/model/native positive and a recent case remain open.
