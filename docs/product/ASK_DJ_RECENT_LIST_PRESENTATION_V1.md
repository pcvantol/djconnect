# Ask DJ recent-list display retention v1

## Reported defect

The original recently-played response has both a full text fallback and `items`.
The Store did not retain those items. Session clients temporarily rendered the
direct-response overlay and removed it at its original action/media deadline,
leaving only text. Rendering both the complete fallback and the cards also
duplicated the same list.

## Optional producer-owned display contract

`recent_history_presentation` is additive on the direct response and its
`assistant_message`, retained Profile messages and source-qualified
`conversation_dj` entries. It contains exactly:

```json
{"schema_version":1,"item_type":"tracks","caption":"Original localized heading:","omitted_count":0,"items":[{"item_id":"recent-0","kind":"track","title":"Original recording","subtitle":"Original performer","played_at":"2026-11-01T15:00:00+00:00"}]}
```

`item_type` is `tracks`, `albums`, `artists` or `playlists`; every item's `kind`
must be its singular counterpart. There are 1–10 original items in original
order. `item_id` is exactly `recent-<original zero-based ordinal>` within this
message's presentation, never a URI or a globally reusable execution ID.
Repeated plays of the same recording remain distinct occurrences. A renderer
combines the original server-message/entry identity with this item ID.

Caption and title are nonempty, trimmed strings of at most512 Unicode code
points; optional subtitle has the same bound. No C0 characters are accepted.
Optional `played_at` is the original provider observation timestamp, normalized
to timezone-aware UTC ISO8601; it is not replaced with read/reconnect time.
Clients may format that timestamp locally. No stored `played_at_label` is used.
`omitted_count` is an integer0–50 (never a boolean); the entire UTF-8 JSON value
is bounded to16,384 bytes. Unknown fields, wrong kinds/ordinals/types, invalid
timestamps and over-limit values invalidate the complete optional value.

## Retention and rights

Only the normal recent-list producer builds the value from the original
provider result and existing localized heading. No fallback-text parsing,
model interpretation or lookup of today's defaults recreates old list items.
The shared application service captures the existing original source authority,
requires its boolean result to be exactly true, and obtains the existing
`async_metadata_archive_admission` before a new Store write. Its original
provider/account/entry binding stays internal. Commit and delivery retain the
existing source/owner/privacy/generation/deletion fences. A duplicate accepted
request reuses its original stored binding; it does not rebind to current defaults.

Profile history and Session timeline reads requalify that original source.
Missing, malformed or withdrawn source authority closes the presentation;
source withdrawal redacts both cards and caption alongside the dependent text.
Normal Profile clear, scoped deletion and retained-entry expiry apply. This is
the existing Store plus reference-backed Session projection, not another store.

No URI, value, image URL, proxy token, action, lease, result set, audio URL,
credential or model-processing permission is retained in this display object.
The original full text remains unchanged for older clients, accessibility and
fallback. A read does not refresh any operational deadline or fetch a provider.

## Rendering and interaction

After validation, render the explicit caption and original cards once instead
of rendering the full duplicate bullet list above them. If validation fails or
the field is absent, retain the complete original text fallback. Retained
display metadata remains separate from the expiring live overlay. Top-level
and direct `assistant_message` values are identical when both are emitted by
Core; if a transport presents conflicting values, clients must close the
optional presentation rather than merge either value into trusted display.

This value is read-only. It cannot manufacture Play Now from old metadata or
extend a live result-set lease. A music-play button needs a fresh existing
server-owned playback action; audio replay remains a separate speech control.
Existing recent-list requests still perform only status/history reads. Native
rendering, actual installed retention and interactive playback require their
own owning-client/runtime evidence.

## Verification scope

`tests/test_ask_dj_recent_presentation.py` covers original Store/reload/clear,
same-recording occurrences, closed-wire rejection, real paired owner/Store/SQL
and history-handler composition with synthetic provider results, expired
operational RAM, Session end, source withdrawal and a false original authority.
These tests do not establish installation, artwork refresh or provider playback.
