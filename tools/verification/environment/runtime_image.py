"""Verification Platform runtime image freshness gate."""

from __future__ import annotations

import os

from tools.verification.docker_release import DEFAULT_IMAGE
from tools.verification.environment.docker_ha import DockerClient
from tools.verification.models import GateResult, GateState
from tools.verification.runtime import RUNTIME_VERSION


class RuntimeImagePuller:
    """Require the published Docker Hub runtime image before a live run."""

    def __init__(self, docker: DockerClient | None = None) -> None:
        self.docker = docker or DockerClient()

    def pull(self) -> GateResult:
        image = os.getenv("DJCONNECT_VERIFICATION_PLATFORM_IMAGE", DEFAULT_IMAGE)
        tag = os.getenv("DJCONNECT_VERIFICATION_PLATFORM_TAG", RUNTIME_VERSION)
        reference = f"{image}:{tag}"
        result = self.docker.run("pull", reference, timeout=300)
        state = GateState.PASS if result.ok else GateState.FAIL
        return GateResult(
            "verification_runtime_image_pull",
            state,
            "Verification Platform runtime image pulled from Docker Hub."
            if result.ok
            else "Verification Platform runtime image could not be pulled from Docker Hub.",
            {
                "image": image,
                "tag": tag,
                "reference": reference,
                "returncode": result.returncode,
                "stdout_tail": result.stdout[-4000:],
                "stderr_tail": result.stderr[-4000:],
            },
        )
