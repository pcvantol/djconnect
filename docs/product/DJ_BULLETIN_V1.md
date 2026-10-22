# DJ Bulletin V1 — Core1291 / Apple182

Status: **implementation in progress in draft Core PR1293**. Intake and reserved
candidate preparation have local synthetic tests. They are not connected to HA
startup, the approved conversation owner, Planner, native Moment admission or
speech yet. There is no installed producer, published bulletin or native claim.
The existing musical queue preview is a separate feature; it is not this news
bulletin.

## Product and ownership

Core collects fixed public RSS/Atom metadata, requires at least two genuinely
different new stories published within the last30minutes, and prepares one
60–110word source-grounded narrative in the current Session language, Mood and
Persona. Source text is untrusted data. Existing configured HA generation is the
only permitted model boundary; this feature introduces no provider, key or
paid-test budget. Generation and a separate grounding/independence/style check
are bounded to two calls per reserved input pair. Failed checks mean silence.

Only the existing Runtime/Planner may accept a ready candidate and publish a
new `dj_bulletin` Moment. Music content has priority. The existing four-level
Presence policy and **same contribution ledger** control dose, spacing, track
tail, freshness and owner/settings admission. There is no separate bulletin
frequency, scheduled announcement time, quota or catch-up queue. Polling is an
internal five-minute technical cadence, not permission to publish. Music-only
produces no bulletin or proactive speech.

Apple182 renders one ordinary owner Flow bubble and uses its existing
“Speel DJ-antwoorden automatisch af” setting and normal Moment speech
admission. No feed/category controls, new settings, screen, audio player,
VibeCast, shared TV, guest projection or notification feature is introduced.
Core must explicitly preserve owner-only delivery through snapshot, events,
recovery and speech; choosing an owner-only field alone is not sufficient proof.

## Fixed source selection and maintenance

Exactly five sources are defined in `bulletin_intake.SOURCES`. Public official
catalogues and actual XML were checked on22October2026. This deliberately uses
attributable public institutional announcements; it is not comprehensive world
news. Low volume in the strict30minute window is expected and means silence.
Do not widen the window, invent news or use observation time to fill a bulletin.

| Source | Literal feed URL | Reuse baseline |
| --- | --- | --- |
| CBS | `https://www.cbs.nl/nl-nl/rss-feeds/alle-nieuwsberichten` | [CC BY4.0, source credit, exceptions apply](https://www.cbs.nl/nl-nl/over-ons/website/copyright) |
| KNMI | `https://cdn.knmi.nl/knmi/xml/rss/rss_KNMInieuwsberichten.xml` | [CC0, exceptions apply](https://www.knmi.nl/copyright) |
| NASA | `https://www.nasa.gov/news-release/feed/` | [NASA media-use guidelines](https://www.nasa.gov/nasa-brand-center/images-and-media/); retain credit, no endorsement, third-party material excluded |
| EEA | `https://www.eea.europa.eu/en/newsroom/rss-feeds/eeas-press-releases-rss/rss.xml` | [CC BY4.0, source credit, exceptions apply](https://www.eea.europa.eu/en/legal-notice) |
| Eurostat | `https://ec.europa.eu/eurostat/en/search?p_p_id=estatsearchportlet_WAR_estatsearchportlet&p_p_lifecycle=2&p_p_state=maximized&p_p_mode=view&p_p_resource_id=atom&_estatsearchportlet_WAR_estatsearchportlet_collection=CAT_PREREL` | [Eurostat reuse conditions and attribution](https://ec.europa.eu/eurostat/help/copyright-notice) |

Source catalogues: [CBS](https://www.cbs.nl/nl-nl/rss-feeds),
[KNMI](https://www.knmi.nl/kennis-en-datacentrum/dataset/rss-feeds-van-het-knmi),
[NASA](https://www.nasa.gov/rss-feeds/),
[EEA](https://www.eea.europa.eu/en/newsroom/rss-feeds),
[Eurostat](https://ec.europa.eu/eurostat/web/rss).
The KNMI constant is the actual verified CDN destination, so no redirect is
needed. Some plausible Rijksoverheid addresses returned HTML/404 and were
excluded. Source URLs inevitably change: maintain constants through code review,
recheck rights and date structure, and silence unavailable sources. No user,
Profile or client can supply an alternative feed or a model-recommended URL.

Only bounded titles and short feed descriptions may enter preparation. No
images, logos, linked full articles or copyrighted third-party extracts are
admitted by this source list. Final source-rights qualification must cover item
exceptions and native attribution before producer delivery; a feed's existence
is not blanket permission for its images or articles. Generated wording must
be identified as a DJ summary with the original source links and times.

## Intake and reservation semantics

The parser accepts RSS2 or Atom, explicit publication dates with timezone, and
HTTPS article links on each source's literal host allowlist. It rejects missing
publication dates, `updated`-only Atom entries, future dates and items at or
beyond publication+1800seconds. CBS's actual explicit `+02:00` spelling is
normalized without inventing a timezone. A304 does not renew original dates.
Intake captures a monotonic deadline before HTTP/lock waits. Builder retains
that deadline and its own original pre-await clock anchor through storage,
generation and assessment. Frozen/backwards UTC cannot grant a fresh lease
after work finishes. Storage quarantine is checked again inside its lock,
including queued preparation and candidate consumption.

HTTP is cancellable with an8second timeout per feed, no redirects, bounded
512KiB decompressed response, bounded XML depth/node count, no DTD/entities,
conditional ETag/Last-Modified and per-source exponential backoff up to1hour.
The lifecycle owner must provide a dedicated cookie-free, credential-free HTTP
session. The collector creates no tasks and cannot publish. At most64 metadata
items per source remain in RAM. Failed publishers do not stop other feeds.

Same URL and tracking-query/GUID changes cannot add a second item. The Builder
also compares normalized titles and conservative token/string similarity,
requires two different publishers, and separately asks the existing generation
owner to assess semantic independence. Two reports of one event are not two
stories. This assessment is not an infallible deterministic event classifier;
cross-language/rewording and unsupported-claim cases remain qualification gates.

Before the first model call, URL/title hashes are durably reserved for24hours
in a bounded256-key backend-internal store. No source text, generated narrative,
Profile or Session ID is written to that dedup store. Unexpired evidence is
never evicted to allow work. Generation failure, timeout, cancellation and
process restart do not release an attempted pair for automatic re-generation.
A lost RAM candidate means silence. A candidate retains the earliest original
publication+30minute deadline on both UTC and monotonic clocks. Reads never
renew it. Planner consumption is once-only; failed publication must not trigger
a second model generation or forced catch-up announcement.

## Integration and qualification still required

1. One HA lifecycle owner for the dedicated HTTP client, storage, cancellable
   collector and candidate preparation; no per-device model work or new endpoint.
2. Original active owner/Session/source/settings authority captured before the
   first await and checked after each await and under the final Runtime lock.
   Normal progress may replace Runtime values; do not require false object
   equality across progress. Owner/Persona/Mood/Presence ABA must invalidate work.
3. Existing Planner opportunity selection, music priority, same Presence debit,
   original candidate expiry, tail fit and immutable `dj_bulletin` semantic commit.
4. Explicit owner-only native display/speech proof and provenance; no shared
   projection, event/recovery leak or new executable action. Initially retain
   only publication metadata in historical storage until content-retention
   rights are separately qualified; do not promote RAM news into an archive.
5. Versioned Core↔Apple golden fixtures for type, sources, original expiry,
   speech admission and unknown older consumers. Apple owns real view/autoplay
   and all native race/accessibility/localization qualification.
6. Actual HA harness, all regressions, security/privacy and independent exact
   review. Current local intake/Builder tests are not these delivery receipts.

All current work stays in the existing draftPR1293. No intermediate merge,
deployment, real provider test, HACS release or native build is implied.
