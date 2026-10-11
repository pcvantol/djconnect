# Versioned documentary maintenance

`djconnect-platform-v1.json` is the single entrypoint. Its original graph,
908 source pins,3October audit/freeze/admission/status observations are unchanged;
`planning_maintenance` records the versioned presence delta and its owner decision.
`history/20261003` preserves the original JSON bytes and original projections.
Canonical and raw SHA256 bindings reject rewriting that frozen content.

The current generated views project only this bounded maintenance delta. They do
not resurvey the portfolio or turn inherited premerge observations into current
blockers. The qualified Mood anchor is scoped to already delivered auth/revision
reuse, not a renewed Mood assignment. No new lane/dispatch/resource lease exists.

Maintenance schema `djconnect-federated-planning-delta/1` uses existing lane IDs,
node identity and edge vocabulary, required subsets/evidence, phase/start or
completion and AND/OR groups. The original historical graph schema remains
`djconnect-federated-planning/1`. `validate_snapshot.py` checks both sections;
`maintenance_delta.py` validates frozen binding, delta IDs, references, authority,
phase/group semantics and acyclicity with the inherited hard graph. The historical
snapshot tests remain on the preserved input; maintenance tests bind local design
source hashes and all generated files, with duplicate/orphan/cycle/false-authority
negative cases. Original require-complete flags describe that historical audit,
not new documentary or product completion. `check_freshness.py` remains a separate
read-only historical-head comparison, not a presence implementation gate.

Update the authoritative JSON delta first, source-document hashes after approved
document changes, and regenerate through the existing route:

```sh
python3 docs/roadmap/v1/render_snapshot.py docs/roadmap/v1/djconnect-platform-v1.json
python3 docs/roadmap/v1/validate_snapshot.py docs/roadmap/v1/djconnect-platform-v1.json --check-rendered
(cd docs/roadmap/v1 && python3 -m unittest test_snapshot test_maintenance_delta)
```

Do not edit only generated Markdown or change the archived historical bytes.
Future maintenance needs its own owner decision, bounded provenance and review.
The presence design's policy budgets/default, actual write/readback contract and
product/native/browser/installed/hardware qualification remain future work.
