# Platform Release Operational Runtime

Status: `QUALIFIED_NON_PRODUCTION`

The operational runtime has two deliberate commands:

- `rehearse`: no-side-effect representative execution using an evidence-only
  client; and
- `execute`: explicit workflow-dispatch orchestration through `gh`.

`execute` requires `--execute`, an approved execution request JSON, a qualified
production/hotfix manifest and an evidence output directory. It can dispatch,
monitor and read workflow evidence only. A command without that acknowledgement
cannot contact GitHub. The request supports only bounded `workflow_dispatch`;
the workflows themselves own any tag, draft-release, artifact-publication,
deployment or rollback operation.

No Platform Release 3.3 execution is implied by this runtime qualification.
Any future 3.3 execution requires a new current-SHA candidate manifest and an
approved internal execution request.
