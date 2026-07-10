"""Compatibility wrapper for result aggregation."""

from .execution.results import ResultAggregator


class ResultManager(ResultAggregator):
    pass


__all__ = ["ResultManager"]
