# Historical recording playback and captured reply artwork v1

## Exact recording, explicit owner tap

A paired Profile owner can negotiate `historical_playback_contract_version:1`
on the existing Session history timeline/open read. Only a retained
`playback_observed` row with its exact Spotify recording URL, original four-field
source/account binding, title, artist and observed-playing coverage offers
`playback_actions`. The original observation proves an observed recording, not
full listening, present availability or successful playback. Ordinary reads
remain passive. Existing unnegotiated history bodies and navigation remain equal.

An action has `kind:historical_track`, `command:play_history_item`, a localized
label, `required_capability:historical_exact_track_playback` and a closed `value`:
`{schema_version:1, session_id, entry_id}`. Send it to the existing paired
`POST /api/djconnect/v1/command` with a stable `client_message_id`. It grants no
caller-supplied URI, search query, account, output or current Session replacement.
The server reopens the original row under current owner/source/retention rights,
then passes its exact recording URI through the common AskDJ effect owner.
Historical Session lifecycle and stored observations remain unchanged.

When no output is active, the existing AskDJ output chooser supplies its normal
server-issued action. Preserve that action and the same original message ID for
transport duplicates. The RAM-only offer retains the original source validator;
it cannot follow a new default account. A choice is consumed before its first
inventory await and may dispatch at most one output/play attempt, including
concurrent requests and uncertain provider outcomes. A rejected/uncertain choice
requires a new explicit human tap, never automatic retry with a new message ID.
Source withdrawal, entry deletion, expiry or owner change closes both steps.
The returned dispatch receipt is not a claim of audible or physical acceptance.
Rows without exact original identity remain readable without a play action;
Moment prose, matching names and the current recording are never substitutes.

## Artwork of the accepted answer

For a newly accepted, persisted Profile AskDJ reply, the existing normalized
image path may capture the exact subject URI and original source binding of an
image actually returned in that answer. A track also needs its original album
URI; an album binds itself; an artist has no album edition. The compact private
`reply_media_reference` lives inside the existing turn receipt. It contains no
CDN URL, pixels, credentials or transferable permission. Public responses,
duplicate receipts, Profile history/export and portable artwork stripping omit
that private binding. Ordinary history reads do not resolve or fetch images.
Legacy and text-only replies remain without captured artwork.

The existing explicit `session/media/prepare` route accepts the retained
`conversation_dj` entry ID. It reopens the exact original accepted assistant
message and prepares its original subject under current source/retention rights.
A reply about another recording never borrows the current recording's cover.
Original album identity must still match provider resolution. Returned media has
`role:captured_reply_subject`, `reply_display_allowed:true`,
`current_display_allowed:false`, `active_flow_display_allowed:false`, and the
existing historical display flag for ended Sessions. The usual attribution,
original expiry, authenticated relative image URL and `no-store` rules apply.

Fresh preparation creates a new temporary media admission; it does not resurrect
old pixels or renew an earlier lease. The existing bounded RAM image owner,
300-second deadline, source/owner checks and deletion barriers remain the only
pixel owner. Source withdrawal or reply deletion during fetch cannot publish
pixels; clearing the owning conversation revokes existing reply resources.
There is no new Store, migration, endpoint, transcript cache or model call.

## Negotiation and qualification

The existing capability contract advertises
`historical_exact_track_playback:true` / version1 and
`captured_reply_artwork:true` / version1. History action negotiation and media
preparation remain independent. Unknown optional actions may be ignored by older
clients; existing schema2 history and artwork transport remain additive.

The owning regressions use the real SQLite archive, Profile storage, paired
common AskDJ application and RAM media owner, with synthetic provider/CDN I/O.
They cover exact old recording versus different current playback, owner/source
revocation, deletion, strict references, duplicate/concurrent/uncertain output
choices, retained reply subject/edition and private export. Synthetic wire
examples live in `examples/client_contracts/history_playback_reply_artwork_v1`.
Protected source, separate Finalization, HA-dev installed/runtime readback and
native/physical/user acceptance each require their own actual evidence.
