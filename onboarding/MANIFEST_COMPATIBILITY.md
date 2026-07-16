# Desired-State Manifest Compatibility Contract

## Independent versioning

The DJConnect developer-onboarding package and a desired-state manifest are
independently versioned artifacts. Updating either one does not implicitly
update the other.

The onboarding package identifies itself with `package.version` in
`onboarding/manifest.yml`. A desired-state manifest must identify itself with
its own semantic `version` field.

## Required manifest fields

A desired-state manifest consumed by an onboarding or runner tool must contain:

```yaml
version: 1.0.0
minimum_tool_version: 1.2.0
```

`minimum_tool_version` is the oldest semantic tool version that understands
the manifest safely. It is an apply-safety boundary, not advisory metadata.
It refers to the consuming tool only; it does not refer to the onboarding
package version or the DJConnect platform-release version.

## Consumer behaviour

At tool startup, before planning or applying desired state, the consumer must:

1. read its own version and the manifest `version`;
2. read `minimum_tool_version`;
3. compare semantic versions numerically; and
4. record the manifest version, tool version and compatibility verdict in its
   log and Markdown report.

If the tool version is lower than `minimum_tool_version`, it must refuse to
apply the manifest. A verification-only invocation may report the incompatible
state but must not claim that the desired state is qualified. A malformed or
missing compatibility field is incompatible by default.

The report verdict must make one of these outcomes explicit:

- `MANIFEST_TOOL_COMPATIBLE`;
- `MANIFEST_TOOL_TOO_OLD`;
- `MANIFEST_COMPATIBILITY_UNVERIFIABLE`.

No secret, token, certificate value or private path belongs in this comparison
or report.
