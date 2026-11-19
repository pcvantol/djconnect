"""Validation hooks for localization, capability and contract checks."""

from __future__ import annotations

from .gates import GateResult


class LocalizationValidator:
    def validate(self) -> GateResult:
        return GateResult("localization_validator", True, "Not implemented in scaffold")


class CapabilityValidator:
    def validate(self) -> GateResult:
        return GateResult("capability_validator", True, "Not implemented in scaffold")


class ContractValidator:
    def validate(self) -> GateResult:
        return GateResult("contract_validator", True, "Not implemented in scaffold")
