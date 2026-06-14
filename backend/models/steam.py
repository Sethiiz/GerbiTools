from __future__ import annotations
from pydantic import BaseModel


class GameEntry(BaseModel):
    name: str
    status: str
    hours: float
    achievements: int
    link_hltb: str


class PlatinumReport(BaseModel):
    steam_id: str
    games: list[GameEntry]
    total: int
    platinados: int
    incompletos: int
    nunca_jogados: int
    privado: bool = False
