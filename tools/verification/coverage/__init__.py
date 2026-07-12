"""Platform-independent coverage capability."""

from tools.verification.coverage.models import (
    CoverageMetric,
    CoverageParseResult,
    CoverageQualification,
    CoverageQualificationStatus,
    CoverageReport,
    CoverageStatus,
    CoverageValidation,
)
from tools.verification.coverage.pipeline import CoveragePipeline
from tools.verification.coverage.registry import CoverageParserRegistry, default_registry

__all__ = [
    "CoverageMetric",
    "CoverageParseResult",
    "CoveragePipeline",
    "CoverageQualification",
    "CoverageQualificationStatus",
    "CoverageReport",
    "CoverageStatus",
    "CoverageValidation",
    "CoverageParserRegistry",
    "default_registry",
]
