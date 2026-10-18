# Ask DJ playable options — 18October2026

Same sole Core writer, existing corrective branch and joint draftPR1197; base
`2efc10dfeaba7fe8c3db8c9b7acfc5220d99faa9`. Main, installed HA-dev and HA-prod
are unchanged by this source correction. No new assignment or consumer write.

## Report and cause

The owner reports “Speel iets van Metallica”: ten results in numbered prose,
ten informational Spotify rows without play, then the same ten actionable rows.
Only the actionable list with art/type/play is desired. The same bubble's speech
button shows “Mislukt”. These are separate observed symptoms.

Both existing Core artist and genre option builders duplicated the catalogue
in `text`, `items` and `playback_actions`. Apple source also only matches track
history items to inline actions, leaving album/playlist rows beside standalone
actions. Core now avoids generating that redundant input for this route. No
Apple source, historic stored response or older installed build is changed.

## Bounded repair

The two builders share one formatter: a short five-language intro, empty `items`,
original playable cards in `playback_actions`. Original deduplication/interleave,
limit, URI/context, proxied artwork and result-set/action IDs remain. No text
parsing, new action type or synthetic play button. An empty search honestly has
no playable actions. Existing informational/history routes retain their data.

The accepted intro is also the exact speech text. Existing prepare1 and Settings3/
prepare3, private MP3 bytes, safe provider-failure notice and original backoff are
exercised without another dialogue/search/playback request or preference write.
Source/Settings/identity revision checks and original deadlines are preserved.
External Spotify and TTS I/O are explicit fixtures; provider-failure injection
is not the cause of the original phone's failure.

## Causal verification and remaining gate

Before production changes, the new ordinary paired-handler regression fails on
the duplicate `items` in all five languages. The original RED log is preserved.
After the change, five new named owner tests cover ten-card delivery, all five
intro languages, empty results, literal prepare/private bytes/cache, Settings3
voice/reference identity, provider failure and safe explicit-replay backoff.
Existing raw artist/genre tests now assert the requested single-list behavior.

Golden adds three steps to the existing search/selection/play family and two
reports:51reports/36families/143steps. The original phone speech failure remains
an explicit open Core finding; twelve Core and seventeen actual-quality findings
remain blocking. No paid calls or editorial-quality PASS follows from these tests.
Full/isolated qualification receipts and exact candidate are attached to the
existing draft/checkpoint after validation.

The original installed phone failure has no captured typed prepare/audio/output
error. Available HA-dev logs show prepare and audio requests around the reported
time but do not bind an HTTP failure or native audio error to this bubble. The
latest bounded tunnel capture has no retained speech request. A working fixture
therefore does not close the original TTS issue or establish audible output.
Actual client-stage failure/readback and controlled installed/native listening
acceptance remain required. No silent provider switch, repeated music request or
reconstruction from visible bubble text is permitted as a workaround.
