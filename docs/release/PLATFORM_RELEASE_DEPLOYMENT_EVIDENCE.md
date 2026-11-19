# Platform Release Deployment Evidence

Status: `IMPLEMENTED`

Deployment is represented as an explicit existing-workflow dispatch action in
the approved execution request. The action carries verified artifact SHA-256
values from its qualified build evidence. The runtime records repository,
workflow/ref, artifact hashes, timestamp, category and workflow-dispatch receipt in
`release-deployment-evidence.json`.

The runtime does not build or deploy on a target device. Existing workflows
produce qualified artifacts on their canonical runners; deployment targets
consume those artifacts. On a failure, no later deployment is dispatched and
the report records `PRESERVE_AND_STOP` rollback evidence.
