"""Run an existing Golden profile and write its validated CI summary."""
from __future__ import annotations

import argparse
import asyncio
import importlib.util
from pathlib import Path
import sys
import types
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
PACKAGE = "djconnect_ci_qualification"


def _load_module(name: str) -> Any:
    spec = importlib.util.spec_from_file_location(
        f"{PACKAGE}.{name}", ROOT / "custom_components" / "djconnect" / f"{name}.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    if spec.loader is None:
        raise ImportError(f"Cannot load qualification module: {name}")
    spec.loader.exec_module(module)
    return module


def _load_qualification_modules() -> tuple[Any, Any]:
    package = types.ModuleType(PACKAGE)
    package.__path__ = [str(ROOT / "custom_components" / "djconnect")]
    sys.modules[PACKAGE] = package
    const = types.ModuleType(f"{PACKAGE}.const")
    const.DOMAIN = "djconnect"
    const.API_IMAGE_PROXY_BASE = "/api/djconnect/v1/image_proxy"
    sys.modules[const.__name__] = const
    try:
        for name in (
            "verification_clock",
            "session_runtime",
            "developer_session_bootstrap",
            "developer_session_scenario_driver",
            "developer_session_capture",
            "structural_invariant_validator",
        ):
            _load_module(name)
        return _load_module("golden_qualification"), _load_module("ci_qualification_report")
    except Exception:
        _unload_modules()
        raise


def _unload_modules() -> None:
    for name in tuple(sys.modules):
        if name == PACKAGE or name.startswith(f"{PACKAGE}."):
            del sys.modules[name]


async def async_run_profile(profile: str) -> dict[str, Any]:
    """Run only an existing profile through its existing Foundation handler."""
    qualification, _ = _load_qualification_modules()
    try:
        handler = {
            "golden_smoke": qualification.async_handle_golden_smoke,
            "golden_regression": qualification.async_handle_golden_regression,
        }[profile]
        return await handler(types.SimpleNamespace(data={}), include_advisory_metrics=True)
    finally:
        _unload_modules()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", choices=("golden_smoke", "golden_regression"), required=True)
    parser.add_argument("--report-path", type=Path, required=True)
    args = parser.parse_args()

    report = asyncio.run(async_run_profile(args.profile))
    _, reporter = _load_qualification_modules()
    try:
        markdown = reporter.render_ci_qualification_report(report)
    finally:
        _unload_modules()
    args.report_path.write_text(markdown, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
