# Maintainer release guidance

Current authority: [release governance](../../CI_CD_RELEASE_GOVERNANCE.md),
[Engineering Method](../../ENGINEERING_METHOD.md) and the applicable approved
candidate/workflow. Protected checks, exact-source review, separate Finalization
and actual installed qualification remain distinct. This document grants no
release, tag, installation or deployment permission.

The old README checklist is retained verbatim below as historical source from
[main8b221d07](https://github.com/pcvantol/djconnect/blob/8b221d07fe2215d9516d18fe92c832332c7a16ab/README.md).
It includes legacy paths and helper commands; do not execute them as a substitute
for current governance. Paths in the transcript are relative to the repository
root. Source checks, five-language review, privacy checks, packaging and actual
installed smoke evidence must not be silently lost during consolidation.

## Original checklist transcript

````text
<details>
<summary>Maintainer release checklist</summary>

Use this checklist for every Home Assistant integration release.

- Confirm the working tree only contains intended changes.
- Check third-party runtime packages, CI tools and local developer tools for
  available updates. Apply safe updates before release; when an update is
  intentionally skipped, record the reason in `HANDOFF.md`.
- Update `custom_components/djconnect/manifest.json` to the target version.
- Update `custom_components/djconnect/const.py` to the same target version.
- Update touched documentation, including `README.md`, `CHANGELOG.md`,
  `AGENTS.md`, `HANDOFF.md`, `TODO.md`, `ISSUES.md`, `SYNC_PROMPTS.md`,
  `PRODUCT_ROADMAP.md`, `TECHNICAL_DESIGN_DECISIONS.md`,
  `CHAT_BOOTSTRAP.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`, `info.md` and
  relevant files under `examples/` where applicable.
- Update and JSON-validate `examples/djconnect.postman_collection.json`
  whenever HTTP endpoints, auth headers, request payloads or response shapes
  change.
- Keep `examples/ask_dj_e2e_cases.json` current for Ask DJ client-visible
  intents.
- Always review all five supported translations: English, Dutch, German,
  French and Spanish. Keep them complete, natural and current for config-flow,
  options-flow, repair-flow, entity, service, endpoint and client-facing text,
  even when the change looks mostly API/docs/client-contract related.
- Re-run security/diagnostics redaction checks when payloads, logs,
  diagnostics, Ask DJ history, memory, push registration or token handling
  changes.
- Add or update tests for new behavior paths, regression risks, translations
  and edge cases.
- Verify `custom_components/djconnect/brand/` contains `icon.png`,
  `icon@2x.png` and `logo.png`.
- Verify `LICENSE`, [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) and the
  dependency inventory in `TECHNICAL_DESIGN_DECISIONS.md` stay current after
  dependency or tool changes.
- Run the lightweight tests:

```bash
python3 -m unittest discover -s tests
```

For focused contract checks:

```bash
python3 -m unittest tests.test_translations
python3 -m unittest tests.test_ask_dj_e2e_contract
python3 -m unittest tests.test_postman_collection
```

Release helper:

```bash
./release.sh X.Y.Z
./release.sh X.Y.Z --dry-run
```

After publishing, verify HACS install/redownload, restart Home Assistant, add or
reload DJConnect, complete pairing/OAuth, open options, check icon/logo and run
the core developer actions.

</details>
````
