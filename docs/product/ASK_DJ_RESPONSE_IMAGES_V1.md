# Ask DJ observed response images V1

## Existing producer and separate client adoption

This documents the existing `images[]` producer in
`reply_artwork.observed_current_image`, protected in Source1409 at
`a4f290734d01fa47918ea10d470e2689b93aa264`. It changes no product bytes.
`reply_artwork.py` SHA256 is
`1a9e7dda046346f55cf48035eea2ad15b26fff72942bf6cbe074a10fe1d041bf`.
An independently qualified server source is not an installed Apple transport or
proof of the reported missing-cover incident's HTTP cause.

A current-track identification may include one optional original observed cover:

```json
{
  "url": "/api/djconnect/v1/ask_dj/reply/image/opaque-original-asset",
  "thumbnail_url": "/api/djconnect/v1/ask_dj/reply/image/opaque-original-asset",
  "title": "Original recording title",
  "subtitle": "Original performer",
  "kind": "album_art",
  "source": "spotify",
  "requires_device_auth": true,
  "expires_at": "2026-11-01T19:00:00+00:00",
  "cache_policy": "no-store"
}
```

The shown timestamp and opaque asset are examples, not usable admissions. A
Session-scoped image instead uses the original
`/api/djconnect/v1/session/media/image/{session_id}/{asset_id}` path. Both routes
use `DJConnectSessionMediaImageView`, ordinary paired-device/Profile/source
authorization and personal-read permission. An asset ID alone is insufficient.

## Transport and lifetime

Clients decode and preserve `requires_device_auth`, `expires_at` and
`cache_policy`. Resolve the original relative route against the original paired
server, with the owning paired request authorization and identity. Never attach
owner credentials to an arbitrary absolute image host or redirect. Use the
existing authenticated no-cache/no-redirect artwork transport; a generic cached
image loader with no owner headers cannot qualify this resource.

Successful bytes have the validated image MIME and response headers
`Cache-Control:no-store`, `Referrer-Policy:no-referrer` and
`X-Content-Type-Options:nosniff`. Missing/expired/withdrawn resources return the
ordinary unavailable response; missing authorization has the normal owner error.
The title/text reply remains usable when optional pixels are unavailable.

The original asset ceiling is the earlier of the turn's remaining original
speech deadline and 60 seconds. Reading, scrolling, retrying or reopening a view
does not renew it. The general Profile route creates no Session. The original
owner, source/account and turn remain bound; Session-scoped resources also retain
the original Session/item. Server RAM custody and byte delivery recheck those
authorities. There is no image on absent original admission or failed fetch.

Client requests and completions retain the original server/owner/response/asset
identity. Discard a late completion after replacement, expiry or withdrawal and
clear its URL and decoded pixels. Preserve the owning expiry/clock handling;
unknown or invalid expiry is not permission to start a new fixed TTL. This
document supplies no new cross-OS clock proof or offline revocation guarantee.
Do not reuse a Now Playing cover, change the URL, forward credentials elsewhere,
or create a new image admission to mask an unavailable original asset.

## Distinction from retained artwork

These short-lived observed `images[]` are separate from the private retained
`reply_media_reference` and the explicit historical `session/media/prepare`
contract in [historical reply artwork](HISTORICAL_PLAYBACK_AND_REPLY_ARTWORK_V1.md).
That preparation's 300-second ceiling cannot extend this observed cover's
original deadline. Neither representation grants playback or native push rights.
Client source, simulator/native rendering, installed transport and actual image
receipt acceptance remain separately owned qualification steps.
