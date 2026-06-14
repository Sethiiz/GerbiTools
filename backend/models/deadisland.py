from __future__ import annotations
from pydantic import BaseModel


class AreaResult(BaseModel):
    name: str
    total: int
    collected: list[int]
    missing: list[int]
    complete: bool


class CollectableReport(BaseModel):
    collected_count: int
    missing_count: int
    total: int
    areas: list[AreaResult]
