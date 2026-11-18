"""CLI self-check for the reusable Software Assurance policy foundation."""

from __future__ import annotations

import json

from .policy import POLICY_ROOT, load_canonical_policy


def main() -> int:
    """Validate canonical policy and shared template without workflow rollout."""
    policy = load_canonical_policy()
    template_path = POLICY_ROOT / "templates" / "workflow-governance.json"
    template = json.loads(template_path.read_text(encoding="utf-8"))
    if template.get("policy_source") != "software_assurance/policy/governance-policy.json":
        raise ValueError("Shared template must reference the canonical policy source.")
    if template.get("rollout", {}).get("enabled") is not False:
        raise ValueError("Shared template must not enable rollout during Prompt 1.")
    print(
        "Software Assurance CI Governance Foundation valid: "
        f"{policy['policy_id']} {policy['policy_version']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
