# Session artist photo v2

Status: local contract/implementation work in the existing Core correction.
No qualified producer pin, protected release, installed or Apple native PASS.

The owner requests a band/artist photograph, preferably a live-performance image,
for a contribution about that artist instead of the current recording's cover.
Spotify remains an image source, not the only one. Album answers, track-list rows
and playback observations retain their exact covers and music controls.

Reuse Session-media preparation, managed bytes, private owner authorization,
source/account fences, expiry, independent history refresh and original Flow
identities. Do not introduce another renderer, image store, scheduler or model.
The delivered version1 contract remains Spotify-only. A client explicitly requests
`contract_version:2` at the same media-prepare endpoint. Version2 may select an
exact primary-performing artist for qualified recording/work-credit Moments and
may use licensed Wikimedia Commons photography when Spotify has no image.
Version1 never starts Commons lookup or changes its cover/attribution semantics.
Separate versioned asset keys prevent one request from replacing the other.

Core retains a typed image identity only after exact catalogue artist link,
MusicBrainz actor and reciprocal Wikidata QID qualification. Identity is for the
performer context: an image of Nirvana does not assert that every guest credited
in a recording is a band member, or depict the specific recording/session. An
album cover cannot stand in for an unavailable artist photo. Missing identity
is unavailable, never a title/name search or borrowed current image.

Commons resolution admits at most three non-deprecated P18 filenames from that
exact QID and one bounded imageinfo/extmetadata batch. If no adequate live image
is available, inspect up to three exact Commons structured-depicts (P180=QID)
results. Search rank is not proof: require actual matching M<pageid> MediaInfo
identity and a non-deprecated P180 statement for the exact QID. No artist-name
query. At most five requests, one selected image and the existing outer 20-second
deadline; no extra attempts after a byte-fetch failure.
P18 establishes the represented subject, not image rights. Require an exact
Commons file page, original SHA1, explicit acceptable license URL/identifier,
creator/credit, attribution, supported still-image MIME, actual validated bytes
and dimensions. Only CC BY/CC BY-SA 2.0/2.5/3.0/4.0 and CC0/public-domain metadata
with their exact known license URLs are in scope. Reject missing/ambiguous
rights, non-commercial/no-derivatives licenses, arbitrary external hosts, SVG,
redirects, unsafe HTML, tiny assets and misleading logo/cover candidates.
Metadata is untrusted data, never markup or instructions for clients/models.

Prefer a qualified candidate whose source description/categories identify a live
performance, then adequate resolution. This is a source-based selection hint,
not a claim that the photo shows the currently playing performance. Do not label
an ordinary portrait as a concert. With no qualified live candidate, an exact
licensed artist photo is preferable to an invented or unrelated concert photo.
Keep original aspect ratio and no crop; no generated band likeness.

Version2 retains the semantic Spotify artist subject and adds its exact QID.
For Commons pixels, `source_url` is the file page, `attribution.provider` is
`Wikimedia Commons`, `mark` is `wikimedia_commons`, with creator, credit,
license ID/URL and image revision. `usage_basis` is
`licensed_artist_image_owner_display`; source metadata is distinct from music
provider attribution. All five alt-text languages remain mandatory. Ready always
means actual validated bytes and a current owner grant, never a planned image.
No Spotify mark may be used as the photograph's author/license attribution.

Store only compact original artist identity alongside the existing retained
media/source reference. History refresh may obtain current qualified pixels
for that original subject; paging/search/replay does not fetch or rewrite text.
Missing old identity cannot be reconstructed by name. A withdrawn provider,
Profile or retained entry invalidates live and historical bytes just as before.
Retention/deletion, Presence, speech/replay and Moment chronology are unchanged.
Private imagery is not granted to shared VibeCast or a receiver by this change.

Apple owns version2 decoder/credit presentation/adoption. Its current strict
version1/Spotify validator intentionally cannot render Commons. Unknown optional
media must preserve text/actions; no native claim until actual consumer proof.
Core will supply pending contract fixtures. Acceptance includes real public
source and photo, source/identity/rights negatives, retained/live races, full
regressions, independent review, and installed/native visual qualification.
A merge or fixture PASS cannot close those gates.

Primary API references: [Imageinfo](https://www.mediawiki.org/wiki/API:Imageinfo),
[CommonsMetadata](https://www.mediawiki.org/wiki/Extension:CommonsMetadata),
[Commons credit lines](https://commons.wikimedia.org/wiki/Commons:Credit_line/en).

The exact structured query and M-page identity are documented by
[Commons depicts](https://commons.wikimedia.org/wiki/Commons:Depicts/fr) and
[structured searching](https://commons.wikimedia.org/wiki/Help:Searching).
The source minimum rejects tiny thumbnails rather than stretching them into a
hero photo. The optional structured lookup can find a larger licensed live image
without changing the original band identity or assuming its members.

The source minimum is 256 pixels on the short side and 320 on the long side, with
a preference for larger qualified live images. A smaller but useful historical
band portrait may be used as a compact contextual image when no qualified live
photo is found. `upscale_allowed:false` and actual decoded width/height prohibit
pretending it is a high-resolution hero. Imageinfo's explicit `thumbnail_unscaled`
original URL must use the original intrinsic dimensions, not requested thumbnail
dimensions; the byte decoder independently verifies them. Tracking-only UTM query
parameters are removed from an otherwise exact Wikimedia upload URL.

Version2 is explicit-response-only. Existing unversioned Broadcast/history media
projections keep version1: a v2 preparation must not overwrite a v1 picture or
make an older client discard it. The requesting v2 client applies its prepare
response to that same target and retains it only for its original grant. It must
ignore optional v1 media for a target while using v2, and invalidate on the
existing authoritative Session/end/Profile/source/history changes and expiry.
No separate v2 scheduler or cross-client unsolicited media event is added.
