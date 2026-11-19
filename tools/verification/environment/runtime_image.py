"""Verification Platform runtime image freshness gate."""

from __future__ import annotations

import os

from tools.verification.environment.docker_ha import DockerClient
from tools.verification.models import GateResult, GateState
from tools.verification.runtime import RUNTIME_DOCKER_REPOSITORY, RUNTIME_VERSION

BASELINE_VERSION = "1.1.0"
BASELINE_DIGEST = "sha256:3f0b8d3ba5f07afa5c8f05cd305dd92c43806e0fed24395be96d832e7ef72619"


class RuntimeImagePuller:
    """Require the published runtime image before a live run."""

    def __init__(self, docker: DockerClient | None = None) -> None:
        self.docker = docker or DockerClient()

    def pull(self) -> GateResult:
        image = os.getenv("DJCONNECT_VERIFICATION_PLATFORM_IMAGE", RUNTIME_DOCKER_REPOSITORY)
        tag = os.getenv("DJCONNECT_VERIFICATION_PLATFORM_TAG", RUNTIME_VERSION)
        if "DJCONNECT_VERIFICATION_PLATFORM_IMAGE" not in os.environ and "DJCONNECT_VERIFICATION_PLATFORM_TAG" not in os.environ:
            if RUNTIME_VERSION != BASELINE_VERSION:
                return GateResult(
                    "verification_runtime_image_pull", GateState.FAIL,
                    "The default runtime digest has not been qualified for this runtime version.",
                    {"runtime_version": RUNTIME_VERSION, "baseline_version": BASELINE_VERSION},
                )
            reference = f"{image}@{BASELINE_DIGEST}"
        else:
            reference = f"{image}:{tag}"
        result = self.docker.run("pull", reference, timeout=300)
        state = GateState.PASS if result.ok else GateState.FAIL
        return GateResult(
            "verification_runtime_image_pull",
            state,
            "Verification Platform runtime image pulled from the configured registry."
            if result.ok
            else "Verification Platform runtime image could not be pulled from the configured registry.",
            {
                "image": image,
                "tag": tag,
                "reference": reference,
                "returncode": result.returncode,
                "stdout_tail": result.stdout[-4000:],
                "stderr_tail": result.stderr[-4000:],
            },
        )
