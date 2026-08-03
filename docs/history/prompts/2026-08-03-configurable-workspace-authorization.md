# Configurable Workspace Root Authorization

Date: 2026-08-03

## Objective

Generalize Engineering Platform workspace-root authorization so a trusted host
configuration can explicitly admit one or more Git repositories without
weakening fail-closed Workspace Preflight. The scope excludes Forge changes,
queue-model changes and arbitrary-path execution.

## Delivered outcome

PR [#719](https://github.com/pcvantol/djconnect/pull/719), **Add configurable
workspace authorization**, merged as
`1fba0b5132d286201c16794adc13f5eaa6e2e6e8`.

The Configuration Resolver now owns a versioned authorization policy with
trusted workspace roots, `direct_children` and explicit `descendants` scopes,
repository allow-lists and deny-lists, symlink policy and host case behavior.
Canonical, path-aware checks reject traversal, prefix lookalikes and symlink
escapes. Deny entries take precedence. Legacy `provisioning_root` behavior is
preserved without authorizing additional siblings.

Workspace Preflight records the stable `WORKSPACE_TARGET_AUTHORIZED` result,
canonical target path, matched authorization and recovery guidance before an
Inbox item can be claimed. Managed requirements remain additional checks;
Genesis still requires a local Git repository but no remote or upstream.

## Validation evidence

- `python3 -m unittest discover -s tests/engineering`: 238 passed.
- Engineering Platform configuration JSON validation: passed.
- `git diff --check`: passed.

## Follow-up

The owner must update trusted local host configuration before retrying a
previously blocked Forge Genesis run. Retry remains explicit; this change does
not resume blocked work automatically.
