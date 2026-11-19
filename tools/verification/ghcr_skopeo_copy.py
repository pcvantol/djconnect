"""Copy only a validated unique probe tag; suppress tool diagnostics."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess

from tools.verification.ghcr_skopeo_probe import MARKER, REPOSITORY


def copy_probe(archive: Path, marker: str, *, run=subprocess.run) -> None:
    if not MARKER.fullmatch(marker):
        raise ValueError("invalid unique probe tag")
    try:
        result = run(["skopeo", "copy", "--preserve-digests", "oci-archive:" + str(archive),
                      "docker://ghcr.io/" + REPOSITORY + ":" + marker],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=180, check=False)
        if result.returncode != 0:
            raise ValueError("copy failed")
    except Exception:
        raise RuntimeError("GHCR probe copy failed; inspect recorded unique tag before cleanup") from None


def main() -> None:
    try:
        copy_probe(Path(os.environ["RUNNER_TEMP"]) / "skopeo-probe/image.tar", os.environ["PROBE_TAG"])
    except Exception:
        raise SystemExit("GHCR probe copy failed; inspect recorded unique tag before cleanup") from None
    print("GHCR probe copy completed; verifying readback")


if __name__ == "__main__":
    main()
