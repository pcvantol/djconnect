# Standalone pipeline owner fixture isolation

The release matrix runs `test_pipeline.py` in its own process. The previous
minimal local fixture installed only `homeassistant.core`. When the genuine
pipeline later imported the genuine Ask DJ dialogue module through its package,
Home Assistant helper imports were missing. Broad test discovery could hide
this fixture dependency by installing the complete HTTP fixture first.

`install_pipeline_stubs()` now explicitly calls the existing named shared
`tests.test_http_voice_helpers.install_http_stubs()` fixture. It keeps the
owning helper API, all22test methods and their assertions, the production
pipeline and the actual Ask DJ dialogue code. The fix does not patch the owning
runner or turn these synthetic owning tests into real HA integration tests.

## Causal evidence

At reviewed Final `f1a5791b8ded2b36c83b282b825c45dd043fccb7`:

- The unchanged standalone runner in the pinned HA image, network `none`, ran22
  tests and wrote a FAIL receipt: two failures and three errors.
- Preloading the existing shared fixture before the same runner and identical
  22executed test IDs produced PASS.
- Mounting this exact minimal proposed test module read-only, without changing
  the owning runner, also produced the identical22-test PASS receipt.

The original first receipt SHA256 is
`ba0cadbcde4d1635f14bc61409b797e40037d123fb9fb993b6cb2885038e239b`;
the shared-fixture and exact proposed-module receipt SHA256 is
`c17f94b15d87d0afd1f71f7d0975af4e24cb9e4079634e40ebbd2a920ddb5431`.
The proposed module SHA256 is
`4f7351fcc00dab7925ce58e69df1f24729caab7b13f0c0e38e2e8aec0287edab`.
The bounded independent diagnosis audit SHA256 is
`b6d4d454c319991ed1ca786656d5c5f836bb4327dc8e1f43aaa1a0facb45c8fd`.
Each disposable container was independently observed absent after cleanup;
there were no mounted credentials, installed HA configuration, network,
provider calls or model calls.

## Qualification boundaries

Both diagnostic variants produced receipts. They do **not** establish why
original automatic workflow39987275546 reported a missing owning receipt.
That historical failure remains retained and unexplained. The one authorized
manual100 run39980138736 remains failed/incomplete, with paid usage unknown and
no retry authority. No workflow, fixed test source, consumed run reservation,
paid grant, artifact allowlist or catalogue flag changes here.

The Help catalogue remains `qualified:false` with70pending examples. All264
product files, release inputs and existing fixtures remain unchanged. This
source requires independent review, normal protected delivery and its separate
Final; no HA restart, production deployment, native push or VibeCast end-to-end
acceptance follows from these unit-fixture results. All24requests and nine
remaining gates remain preserved in the open work register.
