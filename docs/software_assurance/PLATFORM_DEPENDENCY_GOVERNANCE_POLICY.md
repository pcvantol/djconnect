# Platform Dependency Governance Policy

## Purpose

DJConnect uses GitHub-native dependency governance for version-update and
security-update intake. It protects both development and production dependency
graphs without replacing the existing Software Assurance or Trusted Delivery
chain.

## Roles and boundaries

- GitHub Dependency Graph, Dependabot Alerts and Dependabot Security Updates
  are GitHub platform settings.
- Each repository owns `.github/dependabot.yml` and lists only ecosystems it
  actually uses, plus GitHub Actions where workflows exist.
- Dependabot proposes weekly grouped version updates. It does not automerge.
- Existing branch protection continues to require Trusted Delivery; it is not
  a dependency-specific release gate.
- Existing dependency audit and ecosystem-native build/test evidence remain
  repository quality inputs. Dependabot alerts cover direct and transitive
  dependencies according to GitHub's Dependency Graph.
- Lockfiles remain repository-owned source evidence and must change with an
  accepted package-manager update where that ecosystem uses them.
- SHA-pinned Actions remain required; Dependabot may update only the immutable
  SHA and its corresponding version comment.
- TDE 1.1.1 provides canonical non-blocking observe evidence for
  `code_size`, `complexity`, `coverage` and `dependency_health` through the
  public runtime and CLI. It complements, and never replaces, Dependabot,
  dependency audit, Dependency Review where available or ecosystem-native
  vulnerability assessment.

## Supported native ecosystems

The platform currently configures npm, pip, NuGet, Swift and Docker only where
repository source evidence establishes their use, and GitHub Actions across all
active repositories. PlatformIO has no existing GitHub-native Dependabot
adapter and is an explicit exception; its dependency evidence remains in the
existing PlatformIO build/assurance route until a separate qualified decision.

## Risk and exception handling

Dependabot security updates remain enabled in GitHub. A repository may retain a
native-ecosystem exception only when the ecosystem is unsupported by Dependabot
or no manifest is present; the exception must be recorded in the platform
conformance report. This policy adds no new vulnerability database, analyzer,
automerge path or recovery SLO beyond the existing GitHub security update and
Trusted Delivery operating model. TDE remains observe-only and cannot create a
merge or release gate.
