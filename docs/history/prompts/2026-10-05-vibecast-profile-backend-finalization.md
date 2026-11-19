# VibeCast Profile backend binding — Core Finalization

- **Directive:** `DJC-FIRST-SLICE-AFTER-PLANNING-V1-20261003` in
  [central issue #1101](https://github.com/pcvantol/djconnect/issues/1101).
- **Assignment:** `DJC-VIBECAST-PI-OWNER-HANDOFF-V1-20261004`; owning product
  source is `pcvantol/djconnect-app` / DJC-APPLE, with
  [Apple register #87](https://github.com/pcvantol/djconnect-app/issues/87).
- **Core ownership:** The separate Discover Core writer released the sole slot
  for this existing first-slice blocker at clean base
  `a20f570597a68e9a008449c354041889dd26513d`. Discover stayed parked;
  no second Core source writer was started.
- **Source gap:** HA-dev had a Spotify-authorized iOS entry with
  `spotify_direct` options while its bound Profile remained `later_manual`.
  Owner-only Session resolution uses `Profile.preferences.default_backend_id`.
  The existing UI offered no supported existing-Profile reassignment or
  reversible manual backend choice. No direct HA Store edit, credential
  injection or service hack was used.
- **Implementation:** [Core PR #1110](https://github.com/pcvantol/djconnect/pull/1110)
  from reviewed head `4ddf345b61f75f17e0f9e27a6fdd3d77d7677152` protected
  squash-merged as `4531f9f38e6962edfdd9005578804e0f23859fce`. Both trees
  equal `61825c3f3f50ec1d2e93ddd0364518ca711f716a`. The normal
  authenticated music-options route now binds the paired device's
  single-owner Profile to the selected backend in one Profile Store write,
  including same-choice Spotify repair and Later/manual return. Missing OAuth,
  invalid/unbound identity, shared Profile and storage failures fail closed.
  Manual runtime status, commands, diagnostics and Ask DJ actions no longer
  claim Spotify capability; entry reload preserves Music DNA and Ask DJ
  history, while true final-entry unload clears them. Pending Ask DJ playback
  confirmations carry backend revision and are rejected after a switch,
  including after Store reload.
- **Review and validation:** A real independent reviewer found P1/P2 issues
  on earlier heads, each corrected on the same PR. Final exact-head review
  found no remaining P1/P2. Local and independent full suites each ran 1,507
  tests with 7 skips and no failures; Ruff, translation JSON, diff checks and
  applicable protected PR CI passed. A red/green AI-tool Store-reload test
  proved the previous stale confirmation could execute after a backend switch
  and that the corrected route rejects it. The canonical macOS host
  `./scripts/runner/bootstrap_djconnect_macos_host.sh --verify` exited 0 with
  an all-`MATCH` verdict and onboarding package 4.5.3; no repair ran.
- **Exact-main evidence:**
  [Validate](https://github.com/pcvantol/djconnect/actions/runs/37270339152),
  [CodeQL](https://github.com/pcvantol/djconnect/actions/runs/37270338933),
  [artifact run](https://github.com/pcvantol/djconnect/actions/runs/37270556784)
  and [evidence run](https://github.com/pcvantol/djconnect/actions/runs/37270557388)
  succeeded on `4531f9f38e6962edfdd9005578804e0f23859fce`. The unchanged
  workflow published the publicly visible
  [internal SHA prerelease](https://github.com/pcvantol/djconnect/releases/tag/internal-ha-4531f9f38e6962edfdd9005578804e0f23859fce)
  with one HA archive and one redacted qualification JSON. The JSON binds the
  exact commit, reports `POST_MERGE_RELEASE_EVIDENCE_QUALIFIED` and all
  required checks PASS, with coverage digest
  `865666f67e5bf90523c678e9bf0ad64c3851e052f4624fd64c750183ce5747bd`.
  No deployment, stable release, signing or workflow change occurred.
- **Product boundary:** No HA-dev options or Profile preference has yet been
  changed by this source merge. An earlier physical Pi candidate proved
  pairing, snapshot, reconnect, Runtime-end Idle and token non-persistence,
  but was not bound to the final Apple/Core merge SHAs and did not show a real
  non-terminal update during one active Session. `APPLE_SOURCE=MERGED_RECONCILED`,
  `APPLE_WORKSPACE=WORKSPACE_READY`, `PI_QUAL=OPEN`. A supported HA-dev switch,
  exact installed candidate and complete physical receipt remain the sole
  first-slice acceptance work. No Cast or second slice starts here.
- **Finalization:** This governance-only increment updates the four rolling
  records, Product Backlog/Roadmap, VibeCast reference status and this immutable
  Prompt History. Its Execution Horizon is derived afresh from the five
  Planned Platform Evolution backlog items, excluding this completed source
  predecessor. Repository State becomes `MERGED_RECONCILED` only after the
  protected Finalization merge; Workspace State becomes `WORKSPACE_READY` only
  after the mandated safe branch cleanup. The Core writer is released only
  then.
