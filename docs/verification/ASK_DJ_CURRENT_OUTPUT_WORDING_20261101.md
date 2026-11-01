# Current output wording regression

The reported question `welke speaker is nu actief` previously classified as
`ask_music_info` and reached public research. The existing current-output rule
matched `welke speaker is actief` but missed the intervening `nu`.

Bounded Dutch current-output questions now accept `nu` and `momenteel` and the
speaker, luidspreker, uitgang, output and apparaat nouns. They reuse the existing
authorized backend status read and response; they do not select or transfer an
output. The additional grammar matches the whole question, including optional
terminal punctuation. Existing output-list and playback-command routes remain
separate.

The shared message-handler regression uses synthetic provider observations at
the backend boundary and the real conversation owners. Six wording variants
return the freshly observed output with no model, public fetch or playback
effect. A second turn with no current output returns the existing unavailable
message instead of borrowing the previous speaker. Independent review also
reproduced the legacy status helper falling back to a cached speaker when a
fresh status read raised an exception. Current-output questions now disable
that fallback and discard explicitly unsuccessful status responses. Other
callers retain their existing cache behavior. Exception and unsuccessful-response
regressions verify that neither old speaker is described as current.
These are causal routing
checks, not installed-runtime or device acceptance.

The separately reported `Op welk album staat huidige nummer` succeeds against
the current shared message handler in a cost-free diagnostic. Its live failure
has not been identified. HA-dev still contains 277 product files from Source
1382; this change does not claim installation or resolution of that live error.
