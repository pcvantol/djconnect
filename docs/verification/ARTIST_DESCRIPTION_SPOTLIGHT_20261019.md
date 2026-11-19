# Artist description and missing spotlight — 19 October 2026

Status: local source correction; actual installed publication, real prose quality,
provider image and native rendering remain OPEN. No merge or deployment.

The report shows an unsolicited artist story consisting of the Wikidata
"American band" descriptor and no artist picture. Read-only comparison of four
HA-dev files (session_facts, session_artwork, session_runtime and
public_artist_narration) matched exact mainff175834; three differed from the
existing local narrative WIP. This is a partial file comparison, not an installed
full-tree or live-request trace. The screenshot alone cannot establish whether
its image absence came from identity, provider failure or native rendering.

Three concrete source gaps are corrected. Registered artist_begin and
artist_description narration now requires sealed researched acceptance even if
public QID identity is unavailable. Missing identity does not buy symbolic model
calls or publish/count a dry descriptor. The fact is consumed once. Existing
non-artist narration and no-provider behavior are unchanged.

The MusicBrainz link adapter also accepted only `streaming`, missing the official
artist-URL `free streaming` type used for Spotify. Both explicit types now enter
the same exact-URI identity check; ended links are rejected. Official source:
[MusicBrainz artist free-streaming relationship](https://musicbrainz.org/relationship/769085a1-c2f7-4c24-a532-2375a77693bd).
The actual public Nirvana artist-reference read returned503; this schema finding
is not a successful readback of Nirvana's current links or photo.

The Wikidata description previously admitted an image only through its own P1902
Spotify artist claim. The already resolved MusicBrainz artist can instead carry
an exact Spotify streaming URL. Reuse that existing image subject when P1902 is
absent, the original catalogue artist ID matches the explicit link, the exact
artist name/type and MusicBrainz ID match, and MB→QID→MB is reciprocal. A birth or
formation date is irrelevant to this image proof. Conflicting WD references,
wrong actor/name/QID/link, or multiple matching artist IDs do not gain fallback
permission. No name search, current track cover, P18 image or new image adapter.

Existing Session-media delivery and retention remain authoritative: contextual
artist role, no album edition, original provider/account binding, private managed
image URL, owner authentication, source link/mark, original expiry and independent
historical refresh. Store only the compact subject/source reference; never persist
image bytes/CDN delivery URLs in the Flow. History paging does no source lookup or
model rewriting. Read-only Apple source recognizes contextual_artist; that is not
proof of its installed rendering or current application build.

Three new source tests and strengthened existing resolver/unbound-identity tests
cover the exact reciprocal fallback without a formation date; wrong/conflicting
identities; researched Wikidata-story publication; active and reopened SQLite
Flow identity; actual Session-media prepare/image functions with declared external
provider/model fixtures; separate live/historical grants; private managed URLs;
no cover substitution; and replay descriptor/source retention. The fixture pixels
are a synthetic asset, not an actual artist photo. The real image provider and
HA-installed/client rendering are NOT_RUN here. These tests do not prove warm
Persona/Mood writing quality or TTS hearing.

The first focused run passed140tests; the strengthened active/historical image
chain also passed. A complete source run then exposed5failures/7errors in older
tests which expected unbound artist seeds to publish or symbolic model calls.
Generic transport/SQL authority tests now use the existing edition-symbolic
route; legacy no-provider CC0 history tests explicitly exercise that boundary.
Registered artist publication is covered by the separate sealed source/image
chain, without relaxing any production gate. One intermediate focused invocation
was interrupted after a missing standalone host fixture dependency prevented
entry to its awaited model boundary; the existing owner loader now initializes
that fixture explicitly. The updated163owning tests pass. All earlier reports
are retained. Final full suite, lint, inventory and restartable recovery
are recorded in the current checkpoint. Earlier composer and full-catalogue
failures are preserved. No additional paid model call was made in this increment;
the composer preparation's MusicBrainz503 remains an open source gate.

Golden now binds40families/271steps/62reported issues with41release blockers
(17Core findings/24real-quality steps). The new artist-descriptor/spotlight issue
is OPEN. Its real prose/image/native/installed scenario is explicitly open rather
than closed by source tests or by a merge. No wording variants generated.

An intermediate complete source snapshot passed2720tests/7existing skips before
the official relationship-type mismatch was identified. Final source must also
include and retest free-streaming/ended-link handling; that earlier green report
is retained rather than reused as current qualification.
