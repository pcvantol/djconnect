"""Export a deterministic, exact-commit Brand V2 candidate handoff (no publishing).

All bytes come from Git blobs of --revision, never from uncommitted asset WIP.
An exported candidate does not authorize consumer adoption or release.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = "assets/djconnect/brand-v2/manifest.json"


def export(root: Path, revision: str) -> tuple[bytes, dict]:
    if re.fullmatch(r"[0-9a-f]{40}", revision) is None:
        raise ValueError("exact_producer_commit_required")

    def blob(name):
        # A commit pin is authoritative; the working tree is deliberately ignored.
        return subprocess.check_output(["git", "show", f"{revision}:{name}"], cwd=root)

    raw_manifest = blob(MANIFEST)
    manifest = json.loads(raw_manifest)
    names = set(manifest["files"]) | {
        MANIFEST, manifest["master"]["path"], manifest["font"]["path"],
        "tools/branding/fonts/LICENSE.txt", "tools/branding/fonts/PROVENANCE.md",
        "tools/branding/requirements.txt", manifest["alpha_contours"]["path"],
        "scripts/build_brand.py", "scripts/package_brand.py",
        "assets/djconnect/brand-v2/README.md", "LICENSE",
        "assets/djconnect/brand-v2/source/README.txt",
        "assets/djconnect/brand-v2/source/manifest.json",
    }
    micro = manifest.get("micro_source")
    if manifest.get("brand_version") == "2.0.1" and not isinstance(micro, dict):
        raise ValueError("small_icon_source_required")
    if micro:
        names.update(micro[key] for key in ("path", "provenance_path", "upstream_metadata_path", "upstream_prompt_path"))
    assets = {}
    for name in sorted(names):
        if name.startswith("/") or ".." in Path(name).parts:
            raise ValueError("unsafe_asset_path")
        assets[name] = blob(name)
    for name, record in manifest["files"].items():
        if hashlib.sha256(assets[name]).hexdigest() != record["sha256"]:
            raise ValueError("committed_asset_manifest_mismatch:" + name)
    for section in ("master", "font"):
        record = manifest[section]
        if hashlib.sha256(assets[record["path"]]).hexdigest() != record["sha256"]:
            raise ValueError("committed_source_mismatch:" + section)
    if micro:
        for path_key, hash_key in (("path", "sha256"), ("provenance_path", "provenance_sha256"),
                                  ("upstream_metadata_path", "upstream_metadata_sha256"),
                                  ("upstream_prompt_path", "upstream_prompt_sha256")):
            if hashlib.sha256(assets[micro[path_key]]).hexdigest() != micro[hash_key]:
                raise ValueError("committed_small_icon_source_mismatch:" + path_key)
    contour = manifest["alpha_contours"]
    if hashlib.sha256(assets[contour["path"]]).hexdigest() != contour["sha256"]:
        raise ValueError("committed_alpha_contour_mismatch")
    if hashlib.sha256(assets["scripts/build_brand.py"]).hexdigest() != manifest["recipe_sha256"]:
        raise ValueError("committed_recipe_mismatch")
    handoff = {
        "schema_version": 1, "brand_version": manifest["brand_version"],
        "producer_repository": "pcvantol/djconnect", "producer_commit": revision,
        "brand_manifest": MANIFEST, "brand_manifest_sha256": hashlib.sha256(raw_manifest).hexdigest(),
        "master_sha256": manifest["master"]["sha256"],
        "acceptance": "candidate only; protected Core review and explicit consumer acceptance required",
        "consumers": {"apple": "pcvantol/djconnect-app#138", "website": "pcvantol/djconnect-website#62"},
        "files": {name: hashlib.sha256(data).hexdigest() for name, data in assets.items()},
    }
    if micro:
        handoff["micro_source_sha256"] = micro["sha256"]
    assets["handoff.json"] = (json.dumps(handoff, sort_keys=True, indent=2) + "\n").encode()
    output = io.BytesIO()
    # ZIP_STORED avoids compressor-version drift; fixed metadata avoids time/host drift.
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_STORED) as archive:
        for name, data in sorted(assets.items()):
            info = zipfile.ZipInfo(name, date_time=(2026, 10, 19, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)
    return output.getvalue(), handoff


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    data, handoff = export(ROOT, args.revision)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("xb") as destination:
        destination.write(data)
    receipt = {"producer_commit": handoff["producer_commit"],
               "archive_sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data),
               "brand_manifest_sha256": handoff["brand_manifest_sha256"],
               "acceptance": handoff["acceptance"]}
    args.output.with_suffix(args.output.suffix + ".json").write_text(
        json.dumps(receipt, sort_keys=True, indent=2) + "\n")
    print(json.dumps(receipt, sort_keys=True))


if __name__ == "__main__":
    main()
