# Release Process Review

## Summary

Release workflows are mature in source repos, but public release repositories need clearer validation and language hygiene.

## Observations

- HA has `release.sh` and cleanup governance.
- ESP32 builds and publishes firmware artifacts with SHA256 and manifest metadata.
- Pi source publishes tarballs/checksums to `djconnect-pi-releases`.
- Apple/desktop source repos publish unsigned or TestFlight artifacts through dedicated workflows.
- Website deploys through Cloudflare Pages with tests and smoke checks.
- Release-only repos mostly contain public artifacts and README files.

## Gaps

- Release-only repos lack AGENTS guidance.
- Release-only repos lack CI validation.
- Release README wording can lag source behavior.
- Distribution strategy for TestFlight/App Store/Microsoft Store remains a dedicated workstream.

## Recommendations

1. Add AGENTS and foundation pointers to release-only repos.
2. Add or document artifact integrity validation for release-only repos.
3. Refresh release README wording for Music Backend neutrality and current pairing language.
4. Keep release repositories as distribution surfaces only.
5. Run a dedicated Distribution and Release Strategy epic before broad public launch.
