"""Original metadata once journal in actual isolated HA, never a key provider."""
from __future__ import annotations

import asyncio
import json
from unittest.mock import patch

import verify_installation_principal_data_ha as codec_lab
from custom_components.djconnect.installation_once_journal import (
    InstallationOnceError, InstallationOnceJournal, InstallationOnceOwner,
)


class SyntheticOwner(InstallationOnceOwner):
    """Explicit lab witness; no production factory, key, signer or API admission."""
    positive = True
    storage = True
    intent_ack = True

    def validate_policy(self, capacity):
        if capacity != 2:
            raise PermissionError("synthetic_policy")

    def validate_storage(self, persistence):
        if not self.storage:
            raise PermissionError("synthetic_storage")

    def validate_positive(self, original):
        if not self.positive or (original.kind == "bootstrap_signing" and not self.intent_ack):
            raise PermissionError("synthetic_positive")

    def validate_metadata(self, original, result_hash):
        if result_hash != "a" * 64:
            raise PermissionError("synthetic_metadata")


class InstallationOnceLab(codec_lab.InstallationDataLab):
    async def qualify(self, client, identity, headers):
        root = codec_lab.original.ROOT / "tests/fixtures/installation_principal"
        vectors = json.loads((root / "expired-synthetic-records.json").read_text())
        records = vectors["records"]
        service = self.manager._persistent_sessions._persistence
        assert service.readiness.schema_version == 20
        owner = SyntheticOwner()
        journal = InstallationOnceJournal(service, owner, capacity=2)
        text = records["custody_generation_preparation"]["canonical"]
        cases = ["actual_loaded_HA_original_persistence_schema19_WAL_no_live_factory"]
        other = InstallationOnceJournal(service, owner, capacity=2)
        results = await asyncio.gather(journal.async_reserve_generation(text),
            other.async_reserve_generation(text))
        assert sum(r.original is not None for r in results) == 1
        if results[0].original is None:
            journal, other = other, journal
            results.reverse()
        original = results[0].original
        cases.append("two_real_SQL_journals_same_original_only_one_acknowledged_handle")
        for duplicate_journal in (journal, other):
            duplicate = await duplicate_journal.async_reserve_generation(text)
            assert duplicate.state == "EXISTING_DATA_ONLY" and duplicate.original is None
        cases.append("duplicate_and_equal_SQL_cannot_recreate_terminal_or_effect_permission")
        result = await journal.async_settle_metadata(original, "a" * 64)
        assert result.state == "ACKNOWLEDGED_RESULT_METADATA"
        owner.positive = False
        retired = await journal.async_retire(original)
        assert retired.state == "ACKNOWLEDGED_TERMINAL_METADATA" and retired.data.row[6:9] == (2, 2, "a" * 64)
        cases.append("positive_owner_withdrawn_original_reserved_negative_terminal_still_settles")
        owner.positive = True
        arguments = {name: records[kind]["canonical"] for name, kind in {
            "generation": "custody_generation_preparation", "receipt": "custody_public_receipt",
            "subject": "installation_principal_subject", "context": "bootstrap_admission_context",
            "proof": "bootstrap_proof_preparation", "intent": "original_admission_intent"}.items()}
        arguments["original_expected_transcript"] = vectors["R1"]["canonical"]
        owner.intent_ack = False
        try:
            await journal.async_reserve_signing(**arguments)
        except PermissionError:
            pass
        else:
            raise AssertionError("Presented intent DATA substituted actual original ACK")
        cases.append("matching_bootstrap_intent_DATA_does_not_supply_independent_API_ack")
        owner.intent_ack = True
        actual = service.async_in_transaction
        async def lost_ack(operation, **options):
            await actual(operation, **options)
            raise OSError("synthetic_commit_lost_ack")
        with patch.object(service, "async_in_transaction", side_effect=lost_ack):
            unknown = await journal.async_reserve_signing(**arguments)
        assert unknown.state == "UNKNOWN" and unknown.original is None
        duplicate = await journal.async_reserve_signing(**arguments)
        assert duplicate.state == "EXISTING_DATA_ONLY" and duplicate.original is None
        assert duplicate.data.row[6:8] == (0, 0)
        cases.append("actual_commit_lost_ack_retains_consumed_row_without_handle_or_reissue")
        another = json.loads(text)
        another.update(custody_operation_id="00000000-0000-4000-8000-000000000099", expected_local_revision=4)
        try:
            await journal.async_reserve_generation(json.dumps(another, sort_keys=True, separators=(",", ":")))
        except InstallationOnceError:
            pass
        else:
            raise AssertionError("Retired/UNKNOWN capacity was freed")
        cases.append("retired_and_unknown_rows_consume_capacity_no_TTL_or_reset")
        owner.storage = False
        try:
            await journal.async_status(original.operation.operation_id)
        except PermissionError:
            pass
        else:
            raise AssertionError("Lost original storage authority borrowed")
        owner.storage = True
        cases.append("original_storage_port_loss_cannot_borrow_fresh_owner")
        result = await super().qualify(client, identity, headers)
        result["preceding_installation_codec_cases"] = result.pop("cases")
        result["cases"] = cases
        result["registry_CAS_or_once_or_signer_qualification"] = "LOCAL_METADATA_ONCE_ONLY_NOT_REGISTRY_OR_SIGNER"
        result["installation_once_metadata_only"] = True
        result["actual_key_or_sign_effect"] = "NOT_RUN"
        return result


if __name__ == "__main__":
    codec_lab.original.SourceOriginLab = InstallationOnceLab
    asyncio.run(codec_lab.original.main())
