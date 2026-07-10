# Unknowns

- `UNKNOWN` Full Apple pairing persistence key list and APNs entitlement/build
  configuration.
- `UNKNOWN` Complete Apple diagnostic log persistence, rotation and export
  behavior.
- `UNKNOWN` Exact cache invalidation behavior for every Apple/Windows/Pi
  profile switch, logout, stale pairing and clear-history path.
- `UNKNOWN` Full timeout/retry matrix for every client operation.
- `UNKNOWN` Whether any runtime deployments currently use websocket fast paths
  successfully; source and tests confirm implementation but no live runtime was
  exercised in this phase.
- `UNKNOWN` Current public release repository artifact contents were not deeply
  inspected beyond local repo presence and documented ownership.
- `UNKNOWN` Website runtime routes/localization implementation was not relevant
  to adapter protocol work and was not deeply reconstructed.

These unknowns should become verification evidence requests or follow-up
technical archaeology tasks before adapter behavior depends on them.
