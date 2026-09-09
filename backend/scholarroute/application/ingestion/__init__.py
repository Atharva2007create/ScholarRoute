"""Deterministic structured-data ingestion for canonical education records."""

from scholarroute.application.ingestion.contracts import IngestionSummary, SourceContext
from scholarroute.application.ingestion.service import run_ingestion

__all__ = ["IngestionSummary", "SourceContext", "run_ingestion"]
