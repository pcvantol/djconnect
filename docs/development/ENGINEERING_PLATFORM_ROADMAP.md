# Engineering Platform Roadmap

## 1.4 — Remote Engineering Experience

Completed. Canonical status, remote dashboard, inbox watcher, Tailscale
diagnostics and repository handoffs remain local, read-only and without
release, deployment or product authority.

## 1.5 — Platform Productization

Completed and operational. The platform is an independent engineering product
located in this repository as an implementation strategy. Platform Identity,
Workspace Identity, provider and capability registries, configuration
validation and the Public Platform API remove architectural dependence on
DJConnect. Existing commands remain compatibility wrappers.

The completed operational hardening keeps iCloud Drive limited to Inbox
transport, stores canonical prompt archives, status, reports and logs under
`.engineering/`, stops a strict Inbox sequence after `BLOCKED` or `FAILED`, and
provides bounded redacted component logs, report analysis and read-only private
Codex advice. Qualification covers 39 registered scenarios. These are
compatible 1.5 maintenance and evidence improvements, not a 1.6 requirement.
The Engineering Platform CI quality gate measures branch coverage for its five
core execution files and requires each to remain strictly above 80%; exactly
80.00% does not satisfy the contract.

## 1.6 — Repository Extraction Readiness

Planned. Dependency, namespace, import and public-API audits will demonstrate
that extraction is primarily repository movement, not a redesign.

## 2.0 — Versioned Platform Boundary

In review. Engineering Platform `2.0.0` aligns the platform, runner, Inbox
watcher and private dashboard at one major version and raises the fail-closed
minimum version for new engineering prompts. Storage, protocol and lifecycle
formats remain unchanged.

Standalone packaging, repository templates and a generic CLI remain separate
follow-on work until repository-extraction readiness is qualified. The version
bump alone does not move the platform out of this repository or change
authority.

## Policy

Platform code must not acquire DJConnect runtime, Home Assistant, branding or
repository-name dependencies. Consumer-specific presentation and metadata
enter through Workspace configuration or qualified providers only.
