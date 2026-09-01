# DJConnect bootstrap

This is DJConnect's local AI-development entrypoint. Start with the committed
generated projection in `docs/ai-development/`, then read its companion
`DJCONNECT_DEVELOPMENT_EXTENSION.md`. The projection is the sole local copy of
the eight generic AI-development contracts; this repository retains its
product, qualification and historical authority.

For DJConnect orientation, read `REPOSITORY_STATUS.md`, `ENGINEERING_STATUS.md`,
`MANAGEMENT_SUMMARY.md`, `ROADMAP_INDEX.md`, `PROMPT_INDEX.md`, the applicable
DJConnect architecture and product documentation, and the local extension.
Consult `docs/history/prompts/` and Engineering Platform material only when
historical context is required; neither replaces current repository truth.

Validate the committed projection offline:

```sh
python3 docs/ai-development/validate_projection.py \
  --profile djconnect \
  --source-commit ec070e399ff4dbd92e760370002995fe4f4d52d6 \
  --extension-identity DJCONNECT_DEVELOPMENT_EXTENSION
```
