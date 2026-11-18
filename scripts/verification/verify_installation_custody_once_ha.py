"""Actual isolated HA + real SQLite, explicitly inert custody ports only."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path
import tempfile

import verify_installation_once_journal_ha as preceding
from custom_components.djconnect.installation_custody_once import (
    CustodyEffectPort, CustodyOperationOwner, CustodyUnavailable, InstallationCustodyOnce,
)
from custom_components.djconnect.installation_once_journal import InstallationOnceJournal
from custom_components.djconnect.persistence import PersistenceService
from custom_components.djconnect.persistence.sqlite import SQLitePersistenceProvider


class SyntheticCustodyOwner(CustodyOperationOwner):
    def validate_composition(self, journal, port):
        pass

    def validate_attempt(self, original, port):
        if self.retire_when_spent and self.subject._attempts[original.operation_id].attempted:
            self.subject._journal.retire(self.subject._attempts[original.operation_id].reservation)

    def validate_result(self, original, result_hash):
        assert result_hash == "a" * 64

    retire_when_spent = False


class InertPort(CustodyEffectPort):
    """No generator/signer, just public synthetic metadata and a call counter."""
    def __init__(self):
        self.calls = []

    def generate_once(self, original):
        self.calls.append(original.kind)
        return "a" * 64

    def bootstrap_possession_once(self, original):
        self.calls.append(original.kind)
        return "a" * 64


class CustodyOnceLab(preceding.InstallationOnceLab):
    async def qualify(self, client, identity, headers):
        result = await super().qualify(client, identity, headers)
        result["preceding_installation_once_cases"] = result.pop("cases")
        vectors = json.loads((preceding.codec_lab.original.ROOT
            / "tests/fixtures/installation_principal/expired-synthetic-records.json").read_text())
        records = vectors["records"]
        text = records["custody_generation_preparation"]["canonical"]
        cases = []
        with tempfile.TemporaryDirectory(prefix="inert-custody-") as directory:
            for index, retired in enumerate((False, True)):
                service = PersistenceService(Path(directory) / f"once-{index}.db", SQLitePersistenceProvider())
                await service.async_initialize()
                try:
                    owner, port = SyntheticCustodyOwner(), InertPort()
                    journal = InstallationOnceJournal(service, preceding.SyntheticOwner(), capacity=2)
                    subject = InstallationCustodyOnce(journal, owner, port)
                    owner.subject, owner.retire_when_spent = subject, retired
                    value = await subject.async_generate(text)
                    if retired:
                        assert value.state == "UNKNOWN" and port.calls == []
                        row = await journal.async_status(journal._generation(text).operation_id)
                        assert row.row[6:8] == (0, 0)
                        cases.append("reentrant_exact_journal_retirement_before_inert_port_zero_calls")
                    else:
                        assert value.state == "ACKNOWLEDGED_RESULT_METADATA" and port.calls == ["custody_generation"]
                        cases.append("actual_HA_schema19_NEW_ACK_then_one_inert_generation_metadata_result")
                        other = InstallationCustodyOnce(
                            InstallationOnceJournal(service, journal.owner, capacity=2), owner, port)
                        assert (await other.async_generate(text)).state == "EXISTING_DATA_ONLY"
                        assert len(port.calls) == 1
                        cases.append("new_coordinator_equal_SQL_never_recreates_invocation")
                        arguments = {name: records[kind]["canonical"] for name, kind in {
                            "generation": "custody_generation_preparation", "receipt": "custody_public_receipt",
                            "subject": "installation_principal_subject", "context": "bootstrap_admission_context",
                            "proof": "bootstrap_proof_preparation", "intent": "original_admission_intent"}.items()}
                        arguments["original_expected_transcript"] = vectors["R1"]["canonical"]
                        value = await subject.async_bootstrap_possession(**arguments)
                        assert value.state == "ACKNOWLEDGED_RESULT_METADATA"
                        assert port.calls == ["custody_generation", "bootstrap_signing"]
                        cases.append("later_original_API_intent_chain_separate_inert_bootstrap_possession")
                    try:
                        await subject.async_generate(text)
                    except CustodyUnavailable:
                        pass
                    else:
                        raise AssertionError("Spent slot was retried")
                finally:
                    await service.async_close()
        result["cases"] = cases
        result["classification"] = "CLOSED_CUSTODY_METADATA_ONLY"
        result["actual_key_generation_signing_registry_provider_or_native_effect"] = "NOT_RUN"
        return result


if __name__ == "__main__":
    preceding.codec_lab.original.SourceOriginLab = CustodyOnceLab
    asyncio.run(preceding.codec_lab.original.main())
