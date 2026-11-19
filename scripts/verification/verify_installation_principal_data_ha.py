"""Closed DATA codec inside actual HA plus unchanged original Session regression.

Expired public software DATA only. No signing, key generation, registry, model,
provider or native effect. External Spotify/CDN use the existing declared lab.
"""
from __future__ import annotations

import asyncio
import hashlib
import json

import verify_source_origin_http as original
from custom_components.djconnect import installation_principal_data as wire


class InstallationDataLab(original.SourceOriginLab):
    async def qualify(self, client, identity, headers):
        root = original.ROOT / "tests/fixtures/installation_principal"
        vectors = json.loads((root / "expired-synthetic-records.json").read_text())
        records = vectors["records"]
        cases = []
        for kind, vector in records.items():
            result = wire.decode_record(vector["canonical"], record_type=kind)
            assert result.digest == vector["digest"] and result.classification == wire.CLASSIFICATION
        for vector in vectors["statuses"]:
            assert wire.decode_record(vector["canonical"], record_type="operation_status").digest == vector["digest"]
        cases.append("actual_HA_import_and_eleven_closed_families_six_statuses_exact_public_DATA")
        arguments = {name: records[kind]["canonical"] for name, kind in {
            "generation": "custody_generation_preparation", "receipt": "custody_public_receipt",
            "subject": "installation_principal_subject", "context": "bootstrap_admission_context",
            "proof": "bootstrap_proof_preparation"}.items()}
        arguments["original_expected_transcript"] = vectors["R1"]["canonical"]
        chain = wire.check_bootstrap_chain(**arguments)
        assert chain[0].values["custody_epoch"] != chain[2].values["principal_epoch"]
        cases.append("complete_original_primitive_bootstrap_relation_not_actual_install_or_permission")
        withdrawal = {"intent": records["original_admission_intent"]["canonical"],
            "withdrawal": records["original_operation_withdrawal_preparation"]["canonical"]}
        wire.check_original_withdrawal(**arguments, **withdrawal)
        wire.check_retirement_data(tombstone=records["original_admission_retirement_tombstone"]["canonical"],
            **arguments, **withdrawal)
        principal = {"principal": records["installation_principal_record"]["canonical"]}
        wire.check_device_pair_data(pair_join=records["device_pair_join"]["canonical"], **arguments, **principal)
        wire.check_committed_withdrawal_data(withdrawal=records["withdrawal_preparation"]["canonical"], **arguments, **principal)
        cases.append("pending_withdrawal_and_known_result_variants_exact_DATA_no_registry_CAS_claim")
        raw = (root / "api-b6e5-public-vectors.json").read_bytes()
        assert hashlib.sha256(raw).hexdigest() == "ab4ce0f5d69e87f2294a4abef26d73312b69f6667de025cb9771cc3e7d86f54d"
        api = json.loads(raw)
        transcript = wire.decode_transcript(api["body"])
        assert transcript.body_sha256 == api["body_sha256"]
        assert transcript.signing_input_sha256 == api["signing_input_sha256"]
        cases.append("owning_API_original_public_R1_body_domain_JWKpin_and_hashes_exact_no_signature_action")
        proof = json.loads(arguments["proof"])
        for bad in ('{"x":' * 5 + '0' + '}' * 5, " " * 32769,
                    proof["expected_transcript"] + "\n"):
            try:
                wire.decode_record(bad, record_type="bootstrap_proof_preparation")
            except wire.InstallationDataError:
                pass
            else:
                raise AssertionError("Unbounded/noncanonical record accepted")
        changed = dict(arguments)
        changed["proof"] = json.dumps(proof | {"admission_context_sha256": "0" * 64}, sort_keys=True, separators=(",", ":"))
        try:
            wire.check_bootstrap_chain(**changed)
        except wire.InstallationDataError:
            pass
        else:
            raise AssertionError("Wrong original context accepted")
        cases.append("actual_HA_parser_limits_and_wrong_original_relation_reject")
        for role in ("widget_transport", "status_activity_transport"):
            response = await client.get("/api/djconnect/v1/surface_registration/" + role + "/state",
                headers={**headers, "X-DJConnect-Client-Type": "ios"})
            assert response.status == 503, f"Closed role HTTP status: {response.status}"
            assert await response.read() == b'{"version":1,"state":"UNAVAILABLE"}'
        cases.append("actual_original_paired_HTTP_roles_stay_503_no_registration_or_effect")
        result = await super().qualify(client, identity, headers)
        assert len(result["cases"]) == 19
        result["preceding_source_origin_cases"] = result.pop("cases")
        result["cases"] = cases
        result["installation_principal_DATA_only"] = True
        result["registry_CAS_or_once_or_signer_qualification"] = "NOT_RUN"
        result["native_or_provider"] = "NOT_RUN"
        result["frozen_design_sha256"] = wire.DESIGN_SHA256
        result["synthetic_fixture_sha256"] = hashlib.sha256((root / "expired-synthetic-records.json").read_bytes()).hexdigest()
        return result


if __name__ == "__main__":
    original.SourceOriginLab = InstallationDataLab
    asyncio.run(original.main())
