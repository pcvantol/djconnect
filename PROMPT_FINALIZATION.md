# DJConnect finalization

The generated projection owns generic review, finalization, evidence and
handoff mechanics. DJConnect's rolling-record and immutable-history rules are
defined in `DJCONNECT_DEVELOPMENT_EXTENSION.md`; use the current repository
records rather than this historical navigation page as evidence.

For DJConnect local records, Finalization reconciles a verified
`MERGED_UNRECONCILED` predecessor to `MERGED_RECONCILED`. The Finalization pre-push consistency check is defined by `ENGINEERING_METHOD.md` and includes
`python3 -m unittest tests.test_capability_completion_lifecycle`.
