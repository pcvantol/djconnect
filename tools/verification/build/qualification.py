"""Build qualification metadata checks without platform build commands."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from tools.verification.models import ArtifactMetadata, GateResult, GateState


class BuildQualification:
    def qualify(self, artifacts: list[ArtifactMetadata] | None = None) -> list[GateResult]:
        artifacts = artifacts or []
        return [
            self.artifact_metadata(artifacts),
            self.checksums(artifacts),
            self.signing_metadata(artifacts),
            self.entitlements(artifacts),
            self.version_recording(artifacts),
            self.configuration_recording(artifacts),
            self.ci_validation(artifacts),
            self.release_equivalent_tracking(artifacts),
            self.instrumented_tracking(artifacts),
        ]

    def with_checksum(self, artifact: ArtifactMetadata) -> ArtifactMetadata:
        digest = hashlib.sha256(artifact.path.read_bytes()).hexdigest()
        return ArtifactMetadata(**{**artifact.__dict__, "sha256": digest})

    def from_path(
        self,
        path: Path,
        *,
        name: str | None = None,
        build_type: str | None = None,
        release_equivalent: bool = False,
        instrumented: bool = False,
    ) -> ArtifactMetadata:
        artifact = ArtifactMetadata(
            path=path,
            name=name or path.name,
            version=_version_from_manifest(path),
            build_type=build_type,
            configuration={"exists": path.exists(), "size": path.stat().st_size if path.exists() else 0},
            release_equivalent=release_equivalent,
            instrumented=instrumented,
        )
        return self.with_checksum(artifact) if path.exists() and path.is_file() else artifact

    def artifact_metadata(self, artifacts: list[ArtifactMetadata]) -> GateResult:
        state = GateState.PASS if artifacts else GateState.SKIPPED
        return GateResult("artifact_metadata", state, f"{len(artifacts)} artifacts recorded")

    def checksums(self, artifacts: list[ArtifactMetadata]) -> GateResult:
        missing = [artifact.name for artifact in artifacts if not artifact.sha256]
        state = GateState.FAIL if missing else GateState.PASS if artifacts else GateState.SKIPPED
        return GateResult("checksums", state, "Checksums validated", {"missing": missing})

    def signing_metadata(self, artifacts: list[ArtifactMetadata]) -> GateResult:
        return _metadata_gate("signing_metadata", artifacts, "signing")

    def entitlements(self, artifacts: list[ArtifactMetadata]) -> GateResult:
        return _metadata_gate("entitlements", artifacts, "entitlements")

    def version_recording(self, artifacts: list[ArtifactMetadata]) -> GateResult:
        missing = [artifact.name for artifact in artifacts if not artifact.version]
        state = GateState.FAIL if missing else GateState.PASS if artifacts else GateState.SKIPPED
        return GateResult("version_recording", state, "Version metadata checked", {"missing": missing})

    def configuration_recording(self, artifacts: list[ArtifactMetadata]) -> GateResult:
        return _metadata_gate("configuration_recording", artifacts, "configuration")

    def ci_validation(self, artifacts: list[ArtifactMetadata]) -> GateResult:
        return _metadata_gate("ci_validation", artifacts, "ci")

    def release_equivalent_tracking(self, artifacts: list[ArtifactMetadata]) -> GateResult:
        count = sum(1 for artifact in artifacts if artifact.release_equivalent)
        return GateResult("release_equivalent_tracking", GateState.PASS, f"{count} release-equivalent artifacts")

    def instrumented_tracking(self, artifacts: list[ArtifactMetadata]) -> GateResult:
        count = sum(1 for artifact in artifacts if artifact.instrumented)
        return GateResult("instrumented_tracking", GateState.PASS, f"{count} instrumented artifacts")


def _metadata_gate(name: str, artifacts: list[ArtifactMetadata], attribute: str) -> GateResult:
    missing = [artifact.name for artifact in artifacts if not getattr(artifact, attribute)]
    state = GateState.WARNING if missing else GateState.PASS if artifacts else GateState.SKIPPED
    return GateResult(name, state, f"{name} checked", {"missing": missing})


def _version_from_manifest(path: Path) -> str | None:
    manifest = path if path.name == "manifest.json" else path.parent / "manifest.json"
    if not manifest.exists():
        return None
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    value = data.get("version")
    return str(value) if value is not None else None
