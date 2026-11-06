# Native client Golden source protocol

`catalogue.json` is the deterministic inventory compiled from the exact source
pins it contains. It retains all source references, including explicitly pending
native mappings. Its 998 references are not 998 executed or accepted native tests.
`protocol-vectors.json` contains exclusively synthetic parser fixtures and their
expected closed results. The fixture pins identify no real installation, owner,
provider, executable or spending grant. Even its all-PASS labels must reconcile
to `EVIDENCE_PENDING_INDEPENDENT_REVIEW`, never native qualification.

From the repository root, generate an inventory into a new external output file:

```sh
python3 tools/verification/native_client_golden_contract.py --output /absolute/external/new-inventory.json
```

The CLI writes exclusively: existing output is an error. Draft checking adds
`--plan`, `--expected-receipts` and `--expected-app-receipts`; reconciliation also
adds `--evidence`. Independent expected pins must come from separately admitted
original artifacts. Supplying the synthetic fixtures proves grammar only.
There is no execution option, provider connection, HA hook or native driver.

Fast provider-free regression:

```sh
python3 -m unittest tests.test_native_client_golden_contract tests.test_native_golden_attempts
```

For the existing real SDK transport seam, run
`scripts/verification/verify_native_golden_attempt_transport.py` in the pinned HA
image with network disabled; its HTTP responses are explicit offline fixtures.
Real client runs stay manual/release-relevant and require the independent live
gates in `docs/verification/NATIVE_CLIENT_GOLDEN_CONTRACT_V1.md`.
