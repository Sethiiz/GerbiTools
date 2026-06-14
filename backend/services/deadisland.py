from __future__ import annotations

import gzip
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "tools", "DeadIslandCollectables"))

from src.save_parser import parse_save
from src.models import CollectableReport as ParsedReport
from models.deadisland import AreaResult, CollectableReport


def process_save_bytes(file_bytes: bytes) -> CollectableReport:
    data   = gzip.decompress(file_bytes)
    parsed = parse_save(data)
    return _to_api_model(parsed)


def _to_api_model(parsed: ParsedReport) -> CollectableReport:
    return CollectableReport(
        collected_count=parsed.collected_count,
        missing_count=parsed.missing_count,
        total=parsed.total,
        areas=[
            AreaResult(
                name=a.name,
                total=a.total,
                collected=a.collected,
                missing=a.missing,
                complete=a.complete,
            )
            for a in parsed.areas
        ],
    )
