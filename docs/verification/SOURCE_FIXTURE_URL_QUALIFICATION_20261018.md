# Source fixture URL classification — 18 October

Scope: same existing Core correction/Draft1197. The CodeQL check on `f3830c16`
reported six high-severity incomplete-URL-substring matches in two test modules
and the existing isolated HTTP qualification harness. No alert is dismissed and
no scanner, required check or production network policy is changed.

Fixtures must classify the actual URL host, not a source name hidden in a path,
query or userinfo. `scripts/verification/source_fixture_urls.py` parses URL
components, requires HTTPS without credentials and rejects malformed or
unexpected ports. Wikipedia API fixtures require one of the five exact supported
Wikipedia hosts and the exact API path. Producer fixtures route MusicBrainz and
Wikidata by exact host. The English-only probe excludes the other four supported
Wikipedia hosts and the two exact DuckDuckGo search hosts.

The existing artist fixture previously returned a successful synthetic article
for all six negative path/query/userinfo/host-suffix/HTTP/port cases. Its causal
regression was RED before repair; the repaired fixture returns404 for those
locations. Five official hosts and the English-only filter also have explicit
positive/negative coverage. Both tests join an existing Golden owner binding;
the inventory remains49reports/36families/140steps with11Core/17qualityOPEN.

The focused234-test artist/common-dialogue suite passes after repair. The helper
also belongs to both actual harness and release source-hash sets; the gate test
executes the actual harness hash function and rejects evidence missing that file.
Its import follows the harness source-root selection. No source_unchanged claim
can silently omit this classifier.

These are fixture and qualification-boundary proofs, with no paid calls or
actual web retrieval. They do not establish real source truth, narrative quality
or an installed vulnerability/repair. Exact candidate CI must independently
accept the scanner result before this merge gate can be considered satisfied.
