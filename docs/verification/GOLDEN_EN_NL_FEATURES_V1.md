# Golden EN/NL functional addendum

Owner scope: extend the existing suite for **Voor jou**, **Muziek aankondiging**
and the recent informational regressions in English and Dutch. Preserve all five
product localization families and the original twenty-case paid Golden manifest.
This addendum is executed in the existing Advisory Golden Qualification workflow
on PR/main, manual runs and its existing schedule. It adds no release waiver.

Run from a qualified checkout, writing to a new external evidence directory:

```sh
python3 tools/verification/run_golden_en_nl_features.py \
  --output "${TMPDIR}/golden-en-nl-unique-run"
```

The runner mounts the candidate read-only in the pinned Home Assistant image,
disables external networking, executes ordinary paired HTTP/Store flows in both
languages, and runs the recent causal Core regression tests. Each run preserves
raw receipts, failures, source hashes and language. Missing cases, wrong-language
receipts, source drift and provider effects fail the functional result.

| Group | Required observations |
| --- | --- |
| Voor jou | Prepare without playback; select genre then speaker and retain exact mix; one confirmed play; duplicate original message cannot play again; dismissal stays hidden; expired choice has no effect; old Session cannot replace the new offer. |
| Muziek aankondiging | Correct original recording/performer; twenty independent occurrences; repeated same occurrence has no second generation/publication; manual archive replay retains original; text-only blocks automatic speech; original expiry is never renewed. |
| Speech unavailable | English/Dutch provider withdrawal removes obsolete audio, returns an instruction, preserves accepted text/history, and never repeats the original request or playback. |
| Band members and performance | English/Dutch requests follow the complete factual route, retain members and the requested performance from the declared source, and ignore an unrelated current artist or artist-agenda fallback. |
| Composer and topic | English/Dutch selected composer retains its actual role, without promotion to performer/producer; explicit new subject detaches old selected-source dependencies and survives deletion of that old entry. |

External source and model transports are explicitly synthetic for this functional
addendum. Zero paid/model/Spotify calls and zero real speaker effects are expected.
Its PASS establishes route, authority, retention and effect behavior. It does not
qualify actual generated prose, actual public-source truth, real provider readiness,
installation, audible playback, Apple devices or APNs. Existing live Golden and
editorial evidence remain separate, including their historical failures and the
owner-deferred German/French/Spanish remediation. The original 68-item inventory
is not automatically closed by this addendum.

## Original-output readback regression (2026-11-06)

The cost-free functional job also runs `verify_for_you_output_readback_http` for
EN/NL. It exercises the real paired HA/adapters with declared synthetic Spotify
responses: an exact post-transfer player readback with a lagging device inventory
starts the original frozen mix once; a paused old track is not mix confirmation;
an unconfirmed/wrong output never starts the mix or retries its transfer. The
original native13:46 response was unavailable, so this reproduced negative case
is not asserted to identify that particular native failure. Original paid
release qualification and all five UI language families remain unchanged.
