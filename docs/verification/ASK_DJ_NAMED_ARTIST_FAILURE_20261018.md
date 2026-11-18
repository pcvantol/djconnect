# Named artist search and failure locale — 18October2026

Existing sole Core writer, existing branch/Draft1197, source base
`4c2d71d84d55f7147a672b95266d25f494f15f3c`. New root-cause report from the
existing Apple writer follows the owner's request to repair both failures.
No new writer, consumer mutation, provider setting or playback replay.

## Original installed cause

The reported09:13Nirvana failure follows09:12Pearl Jam. Existing HA-dev logs and
same-owner accepted-history metadata bind two different request/exchange IDs to
two assistant replies. Both turns have confirmed Dutch language. There is no
evidence here of one submit producing duplicate assistant records.

Both original errors are `Spotify search found no matching artist`: the
artist lookup fails before requesting top tracks or dispatching playback. These
specific failures are not an output-selection, OAuth, playback-acknowledgement
or missing-capability error. Availability of an output for a future request is
a separate condition; no original request was replayed to find out.

Paired read-only `search_media` with `play:false` reproduces broad top-one
Nirvana→Guns N' Roses and Pearl Jam→Eddie Vedder. The same existing authority
using quoted artist names or `artist:` phrases resolves Nirvana/Pearl Jam to
their correct Spotify artist IDs. No credentials leave process memory/output;
no Spotify mutation, Session write, reset or audible playback is performed.
This proves the bounded query cause, not the quality of all Spotify searches.

The second cause is independent: `_handle_hybrid` omitted the request payload
when constructing failure text. Its helper guessed Dutch from a short word list
that does not recognize the reported wording, then used an English runtime
default despite the actual accepted `nl` turn.

## Repair

Named-artist lookup now sends a quoted `artist:` phrase, inspects at most ten
returned candidates and still requires normalized exact-name equality. Existing
canonical alias bounds remain unchanged. Unrelated/tribute matches remain denied;
no first-result trust, arbitrary fuzzy substitution, output move or retry loop.
Artist profile/albums/top-tracks and named artist media/URI entrypoints share
this qualification. The backend receives a resolved catalogue query; an unparsed
sentence alone cannot authorize the first artist returned. Common natural-language
Ask DJ parsing is preserved and exercised separately.

The original provider payload is kept for existing compact search diagnostics.
Selected artist ID still filters top-track performer credits before dispatch.
Provider401/403/429 errors propagate with their original status; no false artist
fallback or mutation follows. Exact artist media paths are now consistent, while
non-artist searches retain their existing behavior.

Failure text uses the confirmed common-turn language, otherwise valid explicit
request language/locale, then legacy requestless fallback. All five families
ship together. Wire fields, accepted-history identity, retry/effect gates,
selected output and the shared parser are unchanged; no new consumer contract.

Spotify's current [Search reference](https://developer.spotify.com/documentation/web-api/reference/search)
allows the artist filter for artist results and up to ten results per type.
Quoted-phrase results above are additionally measured through installed HA-dev,
not inferred solely from the documentation.

## Qualification and boundaries

Causal RED tests fail on the old locale and broad top-one query. Named owner tests
cover all artist entrypoints, unrelated/tribute denials, selected-credit-only
track dispatch, provider failures, five languages, duplicate request IDs and two
separate questions. The common paired Ask DJ→real parser→real Spotify adapter→
real effect guard is exercised with only external HTTP/token boundaries replaced
by fixtures; each separate Nirvana/Pearl Jam turn dispatches exactly once.

Golden adds three steps and two reports to its existing listening-wish family:
53reports/36families/146steps. The Spotify backend owner file is now explicitly
scheduled and every named binding must execute before any paid phase. Twelve
Core and seventeen actual-quality gates remain open. No broad narrative-quality,
installed repair, real playback or audible PASS follows from owner fixtures.

The installed HA-dev modules still differ from this source. Existing app40324
installation is separate evidence and cannot qualify uninstalled Core bytes.
Exact source/CI/private-artifact/readback status belongs to the current draft and
restartable checkpoint; source/root-cause proof must not be reported as deployment.
