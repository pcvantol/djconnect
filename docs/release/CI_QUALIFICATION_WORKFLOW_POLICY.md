# CI Qualification Workflow Policy

CI / Qualification workflows run on `pull_request`, `push` to `main` and
bounded diagnostic dispatch where already justified. They may lint, test,
generate coverage, perform static/security/dependency analysis, validate a
build or package and emit exact-SHA qualification artifacts.

They must use least privilege, normally `contents: read` and `actions: read`.
They must not receive production or publication credentials and must not deploy,
tag, publish a release, upload to App Store Connect/TestFlight or mutate a
runtime target.

An Actions artifact created by CI is internal qualification evidence, not a
public product publication. CI failure means the candidate is not qualified.
