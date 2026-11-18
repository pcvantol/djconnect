"""Compatibility wrapper for verification configuration loading."""

from .configuration.loader import DEFAULT_EVIDENCE_DIR, DEFAULT_REPORT_DIR, DEFAULT_SCENARIO_PATHS, load_config

__all__ = ["DEFAULT_EVIDENCE_DIR", "DEFAULT_REPORT_DIR", "DEFAULT_SCENARIO_PATHS", "load_config"]
