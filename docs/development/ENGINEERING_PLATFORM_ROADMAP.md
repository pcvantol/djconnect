# Engineering Platform Roadmap

## 1.4 — Remote Engineering Experience

Completed. Canonical status, remote dashboard, inbox watcher, Tailscale
diagnostics and repository handoffs remain local, read-only and without
release, deployment or product authority.

## 1.5 — Platform Productization

Current. The platform is an independent engineering product located in this
repository as an implementation strategy. Platform Identity, Workspace
Identity, provider and capability registries, configuration validation and the
Public Platform API remove architectural dependence on DJConnect. Existing
commands remain compatibility wrappers.

## 1.6 — Repository Extraction Readiness

Planned. Dependency, namespace, import and public-API audits will demonstrate
that extraction is primarily repository movement, not a redesign.

## 2.0 — Standalone Engineering Platform

Planned. Standalone packaging, repository templates and a generic CLI remain
out of scope until 1.6 qualification succeeds.

## Policy

Platform code must not acquire DJConnect runtime, Home Assistant, branding or
repository-name dependencies. Consumer-specific presentation and metadata
enter through Workspace configuration or qualified providers only.
