from __future__ import annotations

import importlib.util
import os
import re
import asyncio

import aiohttp
from models.steam import GameEntry, PlatinumReport

_TOOL_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "tools", "SteamPlatViewer")
)

STEAM_SEM = 25
HLTB_SEM  = 5


def _load(relative: str):
    import sys
    path = os.path.join(_TOOL_ROOT, *relative.split("/"))
    name = "sp_" + relative.replace("/", "_").replace(".py", "")
    spec = importlib.util.spec_from_file_location(name, path)
    mod  = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_steam_mod = _load("src/steam.py")
_hltb_mod  = _load("src/hltb.py")

SteamClient    = _steam_mod.SteamClient
STATUS_PLATINADO  = _steam_mod.STATUS_PLATINADO
STATUS_NEVER      = _steam_mod.STATUS_NEVER
STATUS_INCOMPLETE = _steam_mod.STATUS_INCOMPLETE
hltb_search    = _hltb_mod.search


def _parse_profile(raw: str) -> str:
    raw = raw.strip()
    if re.fullmatch(r"\d{17}", raw):
        return raw
    m = re.search(r"/profiles/(\d{17})", raw)
    if m:
        return m.group(1)
    m = re.search(r"/id/([^/?\s]+)", raw)
    if m:
        return m.group(1)
    return raw


async def build_report(api_key: str, profile: str) -> PlatinumReport:
    async with aiohttp.ClientSession() as session:
        client = SteamClient(session, api_key)

        token = _parse_profile(profile)
        if not re.fullmatch(r"\d{17}", token):
            steam_id = await client.resolve_vanity(token)
        else:
            steam_id = token

        games = await client.get_owned_games(steam_id)

        steam_sem = asyncio.Semaphore(STEAM_SEM)
        hltb_sem  = asyncio.Semaphore(HLTB_SEM)
        entries: list[GameEntry] = []
        lock = asyncio.Lock()

        async def process(game):
            async with steam_sem:
                ach_count = await client.get_achievement_count(game.appid)
            if ach_count == 0:
                return

            async with hltb_sem:
                hltb = await hltb_search(game.name)
            if hltb is None:
                return

            async with steam_sem:
                status = await client.get_player_status(
                    steam_id, game.appid, game.playtime_forever, ach_count
                )

            async with lock:
                entries.append(GameEntry(
                    name=game.name,
                    status=status,
                    hours=hltb.hours,
                    achievements=ach_count,
                    link_hltb=hltb.url,
                ))

        await asyncio.gather(*[process(g) for g in games])
        entries.sort(key=lambda e: e.hours)

        return PlatinumReport(
            steam_id=steam_id,
            games=entries,
            total=len(entries),
            platinados=sum(1 for e in entries if e.status == STATUS_PLATINADO),
            incompletos=sum(1 for e in entries if e.status == STATUS_INCOMPLETE),
            nunca_jogados=sum(1 for e in entries if e.status == STATUS_NEVER),
        )
