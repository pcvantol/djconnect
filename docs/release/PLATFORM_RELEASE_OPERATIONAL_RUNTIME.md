# Platform Release Operational Runtime

Status: `QUALIFIED_NON_PRODUCTION`

The operational runtime has two deliberate commands:

- `rehearse`: no-side-effect representative execution using an evidence-only
  client; and
- `execute`: explicit external internal-release execution through `gh`.

`execute` requires `--execute`, an approved execution request JSON, a qualified
production/hotfix manifest and an evidence output directory. A command without
that acknowledgement cannot mutate GitHub. The request supports existing
workflow dispatch, tag creation and draft prerelease creation only.

No Platform Release 3.3 execution is implied by this runtime qualification.
Any future 3.3 execution requires a new current-SHA candidate manifest and an
approved internal execution request.
