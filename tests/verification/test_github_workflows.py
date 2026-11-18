from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_verification_platform_docker_release_checks_image_before_push() -> None:
    workflow = (
        ROOT / ".github/workflows/verification-platform-docker-release.yml"
    ).read_text(encoding="utf-8")

    inspect_step = workflow.index("Inspect Docker image labels")
    smoke_step = workflow.index("Smoke test Docker image")
    login_step = workflow.index("Log in to GHCR")
    push_step = workflow.index("Publish and verify permitted GHCR tags")

    assert inspect_step < login_step
    assert smoke_step < login_step
    assert login_step < push_step
    assert "docker image inspect" in workflow
    assert "docker run --rm" in workflow
    assert "org.opencontainers.image.version" in workflow
    assert "verification_runtime" in workflow
    assert "packages: write" in workflow
    assert "registry: ghcr.io" in workflow
    assert "publish_from_environment" in workflow
