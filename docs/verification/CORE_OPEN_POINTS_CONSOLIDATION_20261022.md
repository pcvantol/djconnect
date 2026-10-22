# Core open points consolidation — 22 October 2026

Status: work in progress; one Core PR. Peter's direct instruction holds every
future merge until he explicitly says **merge**. Code, tests and independent
review may proceed. This candidate is not installed and is not a release or
native acceptance claim. Previously merged Core1288/1289 were closed separately;
their source, Final, original qualification and unchanged239-file readback are
not repeated here. Consumer implementation remains with the owning lanes.

## Ask DJ mix and genre correction

Reported examples: “heb je lekkere dance mix voor me” followed by “nee
elektronische dance”, and “Maak een house mix” followed by “Techno”. The latter
screenshot shows the genre reply as failed and an uncertain-action response,
without an offered mix play action. These screenshots do not establish the
exact live model output, initial route or provider availability.

The pending-direction path previously restricted a valid semantic genre
selection to its two or three offered examples, and always searched three
individual tracks. The candidate admits only supported Core genre codes,
including techno and dance, but does not require membership in that example
list. It includes the original admitted request, request kind and clarification
question in the existing interpretation call. Positive replacement directions
and whole-proposal refusals remain distinct semantic decisions; negation alone
does not choose a genre. No extra interpretation/model allowance is added.

A selected mix uses the existing read-only Spotify recommendation adapter,
limited to25 distinct valid playable track URIs. At least two tracks are
required. The resulting single `track_mix` action freezes the actual provider
order through existing original result-set/action IDs and Session/source/queue
guards. Nothing is queued or started during suggestion generation. An explicit
play selection uses the existing exact `play_uris` path; replay of the same
accepted client message does not repeat it. This mix action is separate from
the still-open historical-playback queue-preservation requirement.

An empty, unavailable or unusable provider response offers no play button and
uses a five-language availability response saying nothing started. It retains
the original request kind and original pending deadline for a genre correction;
it does not renew the clarification lease or claim an uncertain playback effect.
Provider track names and private catalogue metadata remain local display data
and are not inserted into the model prompt.

The existing adapter uses Spotify's recommendation endpoint, which Spotify's
[official reference](https://developer.spotify.com/documentation/web-api/reference/get-recommendations)
marks deprecated. Its availability is therefore an actual provider result,
not a promise made by this change. There is no fabricated mix, account/OAuth
change, automatic playlist creation or live paid/provider test.

Synthetic regression evidence uses actual dialogue, Profile, Session and
result-set owners with fake model/provider transports. It covers house mix →
unoffered techno, positive electronic correction, preserved request/deadline,
expiry during lookup, invalid/duplicate/unplayable records and explicit ordered
mix playback exactly once. It does not prove the live screenshot's cause or
native Apple presentation. Full checks and independent review remain gates.

## Remaining selected work in this same Core PR

- Human Forecast from the next3–5 actual queued tracks and real genre evidence;
  no invented energy/BPM, exact duration or guaranteed playback.
- Exact historical recording playback while preserving all other queue items
  and their order, or a typed unsupported result where provider semantics cannot
  establish that invariant.
- Accepted-recommendation artwork with exact original owner/recording/source
  admission; captured Ask DJ reply artwork remains a separate delivered producer.
- Track Insight content/measurement qualification; no dummy numeric values.
- Further bounded Core fixes from the retained17-item request registry.

Apple owns catalogue single presentation and play controls, live help retrieval
on every help-icon tap, captured-reply artwork and historical-playback adoption.
Pi owns physical readiness/recovery and display acceptance. API origin evidence
and normal HACS human OAuth engagement remain separately open. This PR grants
no consumer-source, device, provider-consent, extra-model-budget or merge authority.
