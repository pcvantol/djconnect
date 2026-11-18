# Software Assurance Operational Limitations

## GitHub native SHA enforcement

GitHub's `sha_pinning_required` repository setting is not enabled for the
active DJConnect repositories under accepted exception `TD-GITHUB-001`. The
setting rejects the validated cross-repository reusable-workflow architecture
before job creation despite full-SHA workflow and action references.

The operational control is immutable workflow governance: recursive closure
validation and registry consistency are required before delivery, alongside
Trusted Delivery qualification and repository read-back. This limitation must
be re-evaluated on a GitHub platform change, GitHub Support response or future
Platform Evolution.
