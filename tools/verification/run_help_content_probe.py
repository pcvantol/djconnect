"""Reusable trusted development controller; no catalogue publication authority."""

from __future__ import annotations
import argparse
import io
import json
import os
import re
import secrets
import subprocess
import sys
import tarfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.verification import run_help_catalogue_qualification_20261023 as safe
from tools.verification.help_content_probe import (
    MANIFEST,
    CONTENT_PROFILE_ID,
    CONTENT_MODEL,
    execution_profile,
    control_files,
    digest,
    git,
    mode_policy,
    validate_candidate,
    validate_profile_selected_report,
    validate_progress,
    selected_inputs_complete,
    generation_wire_complete,
    structured_playback_inputs_complete,
)

IMAGE = "ghcr.io/home-assistant/home-assistant@sha256:1b64d38f38d922bf9d59336451fd6453e1d614f934456af4ee3d2a51061be3a4"
WORKFLOW = "pcvantol/djconnect/.github/workflows/help-content-development.yml@refs/heads/main"
require = safe.require


def docker(*args, timeout=30, **kwargs):
    return subprocess.run(
        ["docker", *args], capture_output=True, text=True, timeout=timeout, check=False, **kwargs
    )


def image_identity():
    image = docker("image", "inspect", IMAGE)
    require(image.returncode == 0, "IMAGE_UNAVAILABLE")
    metadata = json.loads(image.stdout)[0]
    identity = metadata["Id"]
    require(
        IMAGE in metadata.get("RepoDigests", [])
        and re.fullmatch("sha256:[a-f0-9]{64}", identity)
        and metadata.get("Os") == "linux"
        and metadata.get("Architecture") == "amd64",
        "IMAGE_MISMATCH",
    )
    return identity


def setup_only(root, directory, *, profile=CONTENT_PROFILE_ID):
    """Same Actions host/image/UID/0700, no secret env/input and network-none."""
    descriptor = execution_profile(profile)
    image_id, identity = image_identity(), None
    work = directory / "private-setup"
    work.mkdir(mode=0o700)
    name = "djc-help-content-setup-" + secrets.token_hex(10)
    label = "setup-" + secrets.token_hex(10)
    try:
        created = docker(
            "create",
            "--platform",
            "linux/amd64",
            "--name",
            name,
            "--label",
            "djc.help-content=" + label,
            "--pull=never",
            "--network",
            "none",
            "--user",
            f"{os.getuid()}:{os.getgid()}",
            "--memory",
            "2g",
            "--cpus",
            "2",
            "--pids-limit",
            "256",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges",
            "--entrypoint",
            "python",
            "--workdir",
            "/candidate",
            "-e",
            "PYTHONPATH=/candidate",
            "-e",
            "PYTHONDONTWRITEBYTECODE=1",
            "-e",
            "DJC_SOURCE_ROOT=/candidate",
            "-e",
            "DJC_SAFETY_PROBE=catalogue_golden",
            "-v",
            str(root) + ":/candidate:ro",
            "-v",
            str(work) + ":/lab",
            IMAGE,
            "/candidate/" + control_files(profile)[-1],
            "--qualification-profile", profile,
        )
        require(
            created.returncode == 0 and re.fullmatch("[a-f0-9]{64}", created.stdout.strip()),
            "SETUP_CONTAINER_FAILED",
        )
        identity = created.stdout.strip()
        state(identity, image_id, label)
        with (work / "private.log").open("x") as log:
            result = subprocess.run(
                ["docker", "start", "-a", identity],
                stdout=log,
                stderr=subprocess.STDOUT,
                timeout=120,
                check=False,
            )
        require(result.returncode == 0, "SETUP_FAILED")
        value = safe.report_safe(
            safe.read_work_file(work / "setup-preflight.json", maximum=2048),
            "SYNTHETIC-NEVER-AUTHORIZED-SETUP-ONLY",
        )
        require(
            set(value)
            == {
                "schema",
                "status",
                "actual_HA_setup",
                "uid",
                "request_dispatches",
                "test_credential",
                "openai_version",
                "httpx_version",
                "qualification_profile",
                "first_request_reasoning_effort",
                "first_request_model",
            }
            and value["qualification_profile"] == profile
            and value["first_request_reasoning_effort"] == descriptor["reasoning_effort"]
            and value["first_request_model"] == descriptor["model"]
            and value["schema"] == 1
            and value["status"] == "PASS_SETUP_ONLY_NOT_QUALIFIED"
            and value["actual_HA_setup"] == "FIRST_MODEL_REQUEST_FENCED"
            and value["uid"] == os.getuid()
            and value["request_dispatches"] == 0
            and value["test_credential"] == "SYNTHETIC_ONLY"
            and all(
                re.fullmatch("[0-9]{1,4}(?:\\.[0-9]{1,4}){1,3}", value[k])
                for k in ("openai_version", "httpx_version")
            ),
            "SETUP_RECEIPT_INVALID",
        )
    finally:
        if identity is None:
            found = docker("inspect", name)
            if found.returncode == 0:
                row = json.loads(found.stdout)[0]
                validate_identity(row, row["Id"], image_id, label)
                identity = row["Id"]
        absent = (
            safe.container_absent(name)
            if identity is None
            else cleanup(identity, image_id, label)[2]
        )
        safe.write_json(
            directory / "setup-cleanup.json", {"state": "VERIFIED_ABSENT" if absent else "UNKNOWN"}
        )
        require(absent, "SETUP_CLEANUP_UNKNOWN")
    value["own_container"] = "VERIFIED_ABSENT"
    safe.write_json(directory / "setup-preflight.json", value)


def state(identity, image_id, label):
    result = docker("inspect", identity)
    require(result.returncode == 0, "STATE_UNAVAILABLE")
    row = json.loads(result.stdout)[0]
    validate_identity(row, identity, image_id, label)
    value = row["State"]
    require(
        type(value["Running"]) is bool
        and type(value["ExitCode"]) is int
        and type(value["OOMKilled"]) is bool
        and value["Status"]
        in {"created", "running", "paused", "restarting", "removing", "exited", "dead"},
        "STATE_INVALID",
    )
    return {
        "status": value["Status"],
        "running": value["Running"],
        "exit_code": value["ExitCode"],
        "oom_killed": value["OOMKilled"],
    }


def validate_identity(row, identity, image_id, label):
    require(
        row["Id"] == identity
        and row["Config"]["Image"] == IMAGE
        and row["Config"]["Labels"].get("djc.help-content") == label,
        "CONTAINER_IDENTITY",
    )
    if row["Image"] != image_id:
        # Docker's containerd store exposes the index as Image and the selected
        # platform manifest separately. Classic Docker exposes image config ID.
        descriptor = row.get("ImageManifestDescriptor", {})
        require(
            row["Image"] == IMAGE.split("@")[1]
            and descriptor.get("digest") == image_id
            and descriptor.get("platform", {}).get("architecture") == "amd64"
            and descriptor.get("platform", {}).get("os") == "linux",
            "CONTAINER_IMAGE_JOIN",
        )


def cleanup(identity, image_id, label):
    # identity was captured from our create RPC (or independently joined to our
    # random name/label/image). A failed diagnostic inspect must not leave its
    # already-started paid task running. Docker IDs cannot be reused.
    before = after = None
    try:
        before = state(identity, image_id, label)
    except (OSError, ValueError, KeyError, subprocess.SubprocessError):
        pass
    try:
        try:
            docker("stop", "--time", "5", identity, timeout=12)
        except (OSError, subprocess.SubprocessError):
            pass
        try:
            after = state(identity, image_id, label)
        except (OSError, ValueError, KeyError, subprocess.SubprocessError):
            pass
        if after is None or after["running"]:
            try:
                docker("kill", identity, timeout=10)
            except (OSError, subprocess.SubprocessError):
                pass
    finally:
        # Removal and independent absence inspection must still run if any
        # earlier Docker RPC times out; this immutable ID is already ours.
        try:
            docker("rm", "-f", identity)
        except (OSError, subprocess.SubprocessError):
            pass
    return before, after, safe.container_absent(identity)


def coordinate_profile(coordinate):
    """Only the pre-secret closed request profile, never a report-selected value."""
    profile = coordinate.get("qualification_profile", CONTENT_PROFILE_ID)
    execution_profile(profile)
    return profile


def context(env):
    fixed = {
        "GITHUB_REPOSITORY": "pcvantol/djconnect",
        "GITHUB_REF": "refs/heads/main",
        "GITHUB_WORKFLOW_REF": WORKFLOW,
        "GITHUB_ACTOR": "pcvantol",
        "GITHUB_TRIGGERING_ACTOR": "pcvantol",
        "GITHUB_EVENT_NAME": "workflow_dispatch",
        "GITHUB_RUN_ATTEMPT": "1",
    }
    require(all(env.get(k) == v for k, v in fixed.items()), "CONTEXT_DENIED")
    for name in ("GITHUB_SHA", "DJC_CANDIDATE_SHA", "DJC_CONTROLLER_SHA"):
        require(re.fullmatch("[a-f0-9]{40}", env.get(name, "")) is not None, "SOURCE_INVALID")
    for name in ("DJC_CONTENT_DIGEST", "DJC_PLAN_DIGEST"):
        require(re.fullmatch("[a-f0-9]{64}", env.get(name, "")) is not None, "DIGEST_INVALID")
    require(env["GITHUB_SHA"] == env["DJC_CONTROLLER_SHA"], "CONTROLLER_RESTRICTION_CHANGED")
    require(
        re.fullmatch("[1-9][0-9]{0,19}", env.get("GITHUB_RUN_ID", "")) is not None, "RUN_INVALID"
    )
    mode_policy(env.get("DJC_CONTENT_MODE"))
    profile = env.get("DJC_CONTENT_PROFILE", CONTENT_PROFILE_ID)
    execution_profile(profile)
    return {
        **({"qualification_profile": profile} if profile != CONTENT_PROFILE_ID else {}),
        "controller_sha": env["GITHUB_SHA"],
        "candidate_sha": env["DJC_CANDIDATE_SHA"],
        "content_digest": env["DJC_CONTENT_DIGEST"],
        "plan_digest": env["DJC_PLAN_DIGEST"],
        "mode": env["DJC_CONTENT_MODE"],
        "run_id": env["GITHUB_RUN_ID"],
        "run_attempt": 1,
        "authority": "OWNER_MANUAL_DEVELOPMENT_WITH_ROOT_DURABLE_CONTENT_MODE_CASE_CLAIM",
        "qualification": "NOT_QUALIFIED",
    }


def admission(controller, candidate, coordinate):
    require(
        git(controller, "rev-parse", "HEAD").decode().strip() == coordinate["controller_sha"],
        "CONTROLLER_CHANGED",
    )
    require(
        git(candidate, "rev-parse", "HEAD").decode().strip() == coordinate["candidate_sha"],
        "CANDIDATE_CHANGED",
    )
    pin = validate_candidate(controller, candidate, profile=coordinate_profile(coordinate))
    require(pin["content_digest"] == coordinate["content_digest"], "CONTENT_DIGEST_CHANGED")
    profile = safe.load_profile(controller)
    selected, _, _ = mode_policy(coordinate["mode"])
    require(profile.manifest_digest() == MANIFEST, "QUESTION_MANIFEST_CHANGED")
    if selected:
        all_cases = profile.cases() + profile.chain_cases()
        require(
            [c["id"] for c in all_cases if c["id"] in selected] == list(selected),
            "CASE_SET_CHANGED",
        )
        for case in all_cases:
            if case["id"] in selected and case.get("chain"):
                require(
                    {c["id"] for c in all_cases if c.get("chain") == case["chain"]}
                    <= set(selected),
                    "CHAIN_INCOMPLETE",
                )
    # The controller is protected/qualified. A candidate is ONLY a reviewed
    # development overlay, never misrepresented as already delivered or Final.
    qualification = safe.github_qualification(coordinate["controller_sha"])
    return {
        "coordinates": coordinate,
        "content": pin,
        "original_controller_qualification": qualification,
        "selected_case_ids": list(selected),
        "scope": "DEVELOPMENT_ONLY_NOT_CATALOGUE_OR_INSTALLED_GO",
    }


def snapshot(candidate, directory, pin):
    root = directory / "source-snapshot"
    root.mkdir(mode=0o700)
    raw = git(candidate, "archive", "--format=tar", "HEAD")
    require(len(raw) <= 128 * 1024 * 1024, "SOURCE_ARCHIVE_OVERSIZED")
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:") as archive:
        archive.extractall(root, filter="data")
    # No ignored/untracked bytecode, config or startup module can enter execution.
    verify_snapshot(root, pin)
    for path in root.rglob("*"):
        require(not path.is_symlink(), "SNAPSHOT_SYMLINK_DENIED")
        path.chmod(0o555 if path.is_dir() else 0o444)
    root.chmod(0o555)
    return root


def verify_snapshot(root, pin):
    require(safe.product_hashes(root) == pin["product_hashes"], "SNAPSHOT_PRODUCT_CHANGED")
    profile = safe.profile_source_hashes(root)
    for observer in ("scripts/verification/artist_public_input_receipts.py",
                     "scripts/verification/artist_answer_review_receipts.py"):
        profile[observer] = digest((root / observer).read_bytes())
    require(profile == pin["profile_hashes"], "SNAPSHOT_PROFILE_CHANGED")
    require(
        {name: digest((root / name).read_bytes()) for name in pin["control_hashes"]}
        == pin["control_hashes"],
        "SNAPSHOT_CONTROLLER_CHANGED",
    )


def reserve(path, coordinate):
    _, attempts, seconds = mode_policy(coordinate["mode"])
    value = {
        **coordinate,
        "state": "RESERVED_BEFORE_MODEL_SECRET_READ",
        "max_attempts": attempts,
        "max_output_tokens": 3000,
        "max_seconds": seconds,
        "automatic_retries": 0,
        "Root_claim": "Required before original workflow POST; missing/lost Root ledger never grants a retry",
    }
    safe.write_json(path, value)


def finish(controller, root, directory, work, coordinate, pin, key, code, absent, error):
    selected, attempts, seconds = mode_policy(coordinate["mode"])
    summary = {
        **coordinate,
        "status": "FAIL_OR_INCOMPLETE",
        "error": error,
        "selected_case_ids": list(selected),
        "max_attempts": attempts,
        "max_output_tokens": 3000,
        "max_seconds": seconds,
        "process_exit_code": code,
        "own_container_absent": absent,
        "external_billing": "UNKNOWN_NOT_A_BILLING_RECEIPT",
        "catalogue_publication": "NOT_GRANTED",
        "findings": [],
    }
    progress_name = "diagnostic-progress.json" if selected else "catalogue-progress.json"
    progress = None
    try:
        progress = safe.report_safe(safe.read_work_file(work / progress_name, maximum=16384), key)
        if selected:
            okay = validate_progress(progress, content_digest=pin["content_digest"], mode=coordinate["mode"])
        else:
            from scripts.verification.catalogue_progress import (
                validate_progress as validate_full_progress,
            )

            profile = safe.load_profile(controller)
            okay = validate_full_progress(
                progress,
                case_ids=[c["id"] for c in profile.cases() + profile.chain_cases()],
                manifest=MANIFEST,
            )
        require(okay, "PROGRESS_INVALID")
        safe.write_json(directory / progress_name, progress)
        summary.update(
            sdk_attempts_reserved=progress["sdk_attempts_reserved"],
            sdk_completed_responses=progress["sdk_completed_responses"],
            completed_cases=len(progress["completed_cases"]),
        )
    except (OSError, ValueError, TypeError, KeyError):
        progress = None
        summary["findings"].append("PROGRESS_UNAVAILABLE_OR_INVALID")
    try:
        raw = safe.read_work_file(work / "catalogue-golden.json", maximum=8 * 1024 * 1024)
        report = safe.report_safe(raw, key)
        require(
            report["source_hashes"] == pin["profile_hashes"]
            and report["source_unchanged"] is True
            and report["manifest_sha256"] == MANIFEST,
            "REPORT_SOURCE_BINDING_INVALID",
        )
        safe.write_bytes(directory / "catalogue-golden.json", raw)
        unchanged = safe.product_hashes(root) == pin["product_hashes"]
        if selected:
            valid = progress is not None and validate_profile_selected_report(report, progress, pin=pin, mode=coordinate["mode"],
                profile=coordinate_profile(coordinate))
            inputs = selected_inputs_complete(report, mode=coordinate["mode"])
        else:
            from scripts.verification.artist_public_input_receipts import (
                artist_public_inputs_complete,
            )

            profile = safe.load_profile(controller)
            valid = profile.validate_report(report, source_hashes=pin["profile_hashes"],
                expected_profile=coordinate_profile(coordinate))
            inputs = artist_public_inputs_complete(report)
            from scripts.verification.askdj_example_catalogue_golden import cases, chain_cases

            inputs = inputs and generation_wire_complete(report, cases=cases())
            inputs = inputs and structured_playback_inputs_complete(report, cases=cases() + chain_cases())
            valid = (
                valid
                and inputs
                and progress is not None
                and progress["outcome"] == "COMPLETE_NOT_QUALIFIED"
                and not progress["failed_cases"]
                and len(progress["completed_cases"]) == 100
            )
            valid = (
                valid
                and progress["sdk_attempts_reserved"]
                == progress["sdk_completed_responses"]
                == len(report["model_calls"])
                == report["paid_model_calls"]
            )
        from scripts.verification.artist_answer_review_receipts import answer_word_reviews_complete
        expected_artist_cases = [row['id'] for row in report['cases']
            if row['id'].startswith('catalogue-listen.artist-')]
        word_inputs = answer_word_reviews_complete(report, expected_cases=expected_artist_cases)
        inputs = inputs and word_inputs
        valid = valid and word_inputs
        summary['original_answer_word_reviews_complete'] = word_inputs
        summary.update(
            report_sha256=digest(raw),
            source_before_after_equal=unchanged,
            original_public_inputs_complete=inputs,
            strict_validator=bool(valid),
            case_results=[
                {"id": r["id"], "status": r["status"], "findings": r["findings"]}
                for r in report["cases"]
            ],
        )
        if code == 0 and error == "NONE" and absent and unchanged and valid:
            summary["status"] = (
                "PASS_TARGETED_DEVELOPMENT_NOT_FULL100"
                if selected
                else "PASS_FULL100_EXECUTION_PENDING_EDITORIAL_AND_DELIVERY"
            )
    except (OSError, ValueError, TypeError, KeyError, AssertionError):
        summary["findings"].append("REPORT_UNAVAILABLE_OR_INVALID")
    for stage in ("IMPORT", "MAIN", "TERMINAL"):
        try:
            value = safe.report_safe(
                safe.read_work_file(work / ("child-" + stage + ".json"), maximum=1024), key
            )
            require(
                set(value) == {"schema", "stage", "error", "qualification"}
                and type(value["schema"]) is int and value["schema"] == 1
                and value["stage"] == stage
                and value["error"] == "NONE"
                and value["qualification"] == "NOT_QUALIFIED",
                "CHILD_DIAGNOSTIC_INVALID",
            )
            safe.write_json(directory / ("child-" + stage + ".json"), value)
        except (OSError, ValueError, TypeError, KeyError):
            summary["findings"].append("CHILD_" + stage + "_UNAVAILABLE")
    if summary["findings"]:
        summary["status"] = "FAIL_OR_INCOMPLETE"
    safe.write_json(directory / "summary.json", summary)
    return 0 if summary["status"].startswith("PASS_") else 1


def execute(controller, root, directory, coordinate, pin, env):
    profile = coordinate_profile(coordinate)
    descriptor = execution_profile(profile)
    _, _, seconds = mode_policy(coordinate["mode"])
    wall_end, mono_end = time.time() + seconds, time.monotonic() + seconds
    identity = image_id = name = None
    key = ""
    code = None
    absent = True
    error = "UNKNOWN"
    primary = None
    work = directory / "private-work"

    def remaining(reserve_seconds=0):
        value = min(wall_end - time.time(), mono_end - time.monotonic()) - reserve_seconds
        require(value > 0, "BUDGET_EXPIRED")
        return value

    try:
        admitted = json.loads((directory / "admission.json").read_text())
        require(
            admitted["coordinates"] == coordinate and admitted["content"] == pin
            and pin.get("execution_profile") == descriptor,
            "ADMISSION_CHANGED",
        )
        readiness = json.loads((directory / "setup-preflight.json").read_text())
        require(
            readiness.get("status") == "PASS_SETUP_ONLY_NOT_QUALIFIED"
            and readiness.get("own_container") == "VERIFIED_ABSENT"
            and readiness.get("qualification_profile") == profile
            and readiness.get("first_request_reasoning_effort") == descriptor["reasoning_effort"]
            and readiness.get("first_request_model") == descriptor["model"],
            "SETUP_NOT_READY",
        )
        require(context(env) == coordinate, "CONTEXT_CHANGED")
        image_id = image_identity()
        reserve(directory / "once-reservation.json", coordinate)
        work.mkdir(mode=0o700)
        # Capture only the public fixed descriptor before any credential read.
        # The child rejects a missing/changed selector against this exact file.
        safe.write_json(work / "execution-profile.json", descriptor)
        key = env.get("DJCONNECT_GOLDEN_OPENAI_API_KEY", "")
        require(type(key) is str and 20 <= len(key) <= 8192, "CREDENTIAL_UNAVAILABLE")
        name = "djc-help-content-" + secrets.token_hex(10)
        selected = ",".join(mode_policy(coordinate["mode"])[0])
        absent = False
        command = [
            "create",
            "--platform",
            "linux/amd64",
            "-i",
            "--name",
            name,
            "--label",
            "djc.help-content=" + coordinate["run_id"],
            "--pull=never",
            "--user",
            f"{os.getuid()}:{os.getgid()}",
            "--network",
            "bridge",
            "--memory",
            "2g",
            "--cpus",
            "2",
            "--pids-limit",
            "256",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges",
            "--entrypoint",
            "python",
            "--workdir",
            "/candidate",
            "-e",
            "PYTHONPATH=/candidate",
            "-e",
            "PYTHONDONTWRITEBYTECODE=1",
            "-e",
            "DJC_SOURCE_ROOT=/candidate",
            "-e",
            "DJC_SAFETY_PROBE=catalogue_golden",
            "-e",
            "DJC_CONTENT_MODE=" + coordinate["mode"],
            "-e",
            "DJC_CONTENT_PROFILE=" + profile,
            "-e",
            "DJC_CONTENT_DIGEST=" + coordinate["content_digest"],
            "-e",
            "DJC_CATALOGUE_CASES=" + selected,
            "-e",
            "DJC_CONTENT_WALL_END=" + str(wall_end - 30),
            "-e",
            "DJC_CONTENT_MONO_END=" + str(mono_end - 30),
            "-v",
            str(root) + ":/candidate:ro",
            "-v",
            str(work) + ":/lab",
            IMAGE,
            "/candidate/tools/verification/help_content_probe_child.py",
        ]
        created = docker(*command, timeout=min(30, remaining(30)))
        require(
            created.returncode == 0 and re.fullmatch("[a-f0-9]{64}", created.stdout.strip()),
            "CREATE_FAILED",
        )
        identity = created.stdout.strip()
        require(
            state(identity, image_id, coordinate["run_id"])["status"] == "created",
            "CONTAINER_STATE",
        )
        safe.write_json(
            directory / "container-created.json", {"identity": identity, "image": image_id}
        )
        with (work / "private.log").open("x") as log:
            child = subprocess.Popen(
                ["docker", "start", "-a", "-i", identity],
                stdin=subprocess.PIPE,
                text=True,
                stdout=log,
                stderr=subprocess.STDOUT,
            )
            payload = json.dumps({"api_key": key, "model": CONTENT_MODEL, "max_tokens": 3000})
            try:
                while True:
                    try:
                        child.communicate(input=payload, timeout=min(0.5, remaining(20)))
                        break
                    except subprocess.TimeoutExpired:
                        payload = None
                code = child.returncode
            finally:
                if child.poll() is None:
                    child.kill()
                    child.wait(timeout=5)
        error = "NONE" if code == 0 else "CHILD_EXIT_NONZERO"
    except BaseException as exc:
        primary = exc
        error = (
            "TIMEOUT" if isinstance(exc, subprocess.TimeoutExpired) else "SETUP_OR_EXECUTION_FAILED"
        )
    finally:
        if name is not None and identity is None:
            try:
                found = docker("inspect", name)
                if found.returncode == 0:
                    row = json.loads(found.stdout)[0]
                    validate_identity(row, row["Id"], image_id, coordinate["run_id"])
                    identity = row["Id"]
                else:
                    absent = safe.container_absent(name)
            except BaseException:
                absent = False
        if identity is not None:
            try:
                before, after, absent = cleanup(identity, image_id, coordinate["run_id"])
                safe.write_json(
                    directory / "container-state.json",
                    {"before_cleanup": before, "after_stop": after},
                )
            except BaseException:
                absent = False
        try:
            safe.write_json(
                directory / "cleanup.json",
                {"state": "VERIFIED_ABSENT" if absent else "UNKNOWN", "identity": identity},
            )
        except BaseException:
            absent = False
        try:
            outcome = finish(
                controller, root, directory, work, coordinate, pin, key, code, absent, error
            )
        except BaseException:
            outcome = 1
            try:
                safe.write_json(
                    directory / "summary.json",
                    {
                        **coordinate,
                        "status": "FAIL_OR_INCOMPLETE",
                        "error": "REPORT_VALIDATION_FAILED",
                        "own_container_absent": absent,
                        "sdk_attempts_reserved": None,
                        "external_billing": "UNKNOWN_NOT_A_BILLING_RECEIPT",
                    },
                )
            except BaseException:
                pass
        key = ""
    if primary is not None:
        raise primary
    return outcome


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--candidate-root", type=Path, required=True)
    p.add_argument("--controller-root", type=Path, required=True)
    p.add_argument("--report-dir", type=Path, required=True)
    p.add_argument("--phase", choices=["admit", "setup", "execute"], required=True)
    a = p.parse_args()
    os.umask(0o077)
    directory = a.report_dir.resolve()
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    coordinate = context(os.environ)
    controller = a.controller_root.resolve()
    candidate = a.candidate_root.resolve()
    if a.phase == "admit":
        value = admission(controller, candidate, coordinate)
        safe.write_json(directory / "admission.json", value)
        return 0
    admitted = json.loads((directory / "admission.json").read_text())
    require(admitted["coordinates"] == coordinate, "ADMISSION_CHANGED")
    pin = admitted["content"]
    require(validate_candidate(controller, candidate,
        profile=coordinate_profile(coordinate)) == pin, "CANDIDATE_CHANGED")
    if a.phase == "setup":
        root = snapshot(candidate, directory, pin)
        setup_only(root, directory, profile=coordinate_profile(coordinate))
        return 0
    root = directory / "source-snapshot"
    verify_snapshot(root, pin)
    return execute(controller, root, directory, coordinate, pin, os.environ)


if __name__ == "__main__":
    sys.dont_write_bytecode = True
    try:
        raise SystemExit(main())
    except (ValueError, OSError, subprocess.SubprocessError):
        print("HELP_CONTENT_DEVELOPMENT=FAIL_CLOSED", file=sys.stderr)
        raise SystemExit(1) from None
