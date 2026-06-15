from __future__ import annotations

import importlib.util
import json
import os
import re
import asyncio
from typing import AsyncGenerator

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

SteamClient       = _steam_mod.SteamClient
STATUS_PLATINADO  = _steam_mod.STATUS_PLATINADO
STATUS_NEVER      = _steam_mod.STATUS_NEVER
STATUS_INCOMPLETE = _steam_mod.STATUS_INCOMPLETE
STATUS_PRIVATE    = _steam_mod.STATUS_PRIVATE
hltb_search       = _hltb_mod.search


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

        summary = await client.get_player_summary(steam_id)
        is_private = summary.get("communityvisibilitystate", 3) != 3

        games = await client.get_owned_games(steam_id)

        steam_sem = asyncio.Semaphore(STEAM_SEM)
        hltb_sem  = asyncio.Semaphore(HLTB_SEM)
        entries: list[GameEntry] = []
        lock = asyncio.Lock()
        private_count = 0

        async def process(game):
            nonlocal private_count
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

            if status == STATUS_PRIVATE:
                private_count += 1
                return

            async with lock:
                entries.append(GameEntry(
                    name=game.name,
                    status=status,
                    hours=hltb.hours,
                    achievements=ach_count,
                    link_hltb=hltb.url,
                ))

        total_games = len(games)
        await asyncio.gather(*[process(g) for g in games])
        entries.sort(key=lambda e: e.hours)

        return PlatinumReport(
            steam_id=steam_id,
            games=entries,
            total=len(entries),
            platinados=sum(1 for e in entries if e.status == STATUS_PLATINADO),
            incompletos=sum(1 for e in entries if e.status == STATUS_INCOMPLETE),
            nunca_jogados=sum(1 for e in entries if e.status == STATUS_NEVER),
            privado=is_private or private_count >= total_games * 0.20,
        )


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


async def build_report_stream(api_key: str, profile: str) -> AsyncGenerator[str, None]:
    try:
        async with aiohttp.ClientSession() as session:
            client = SteamClient(session, api_key)

            token = _parse_profile(profile)
            if not re.fullmatch(r"\d{17}", token):
                steam_id = await client.resolve_vanity(token)
            else:
                steam_id = token

            summary = await client.get_player_summary(steam_id)
            is_private = summary.get("communityvisibilitystate", 3) != 3

            games = await client.get_owned_games(steam_id)
            total = len(games)

            yield _sse({"type": "start", "total": total, "privado": is_private})

            steam_sem = asyncio.Semaphore(STEAM_SEM)
            hltb_sem  = asyncio.Semaphore(HLTB_SEM)
            entries: list[GameEntry] = []
            lock  = asyncio.Lock()
            queue: asyncio.Queue = asyncio.Queue()
            private_count = 0

            async def process(game):
                nonlocal private_count
                try:
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
                    if status == STATUS_PRIVATE:
                        private_count += 1
                        return
                    async with lock:
                        entries.append(GameEntry(
                            name=game.name,
                            status=status,
                            hours=hltb.hours,
                            achievements=ach_count,
                            link_hltb=hltb.url,
                        ))
                finally:
                    await queue.put(None)

            gather_fut = asyncio.gather(*[process(g) for g in games], return_exceptions=True)

            privacy_emitted = is_private
            for processed in range(1, total + 1):
                await queue.get()
                if private_count >= total * 0.20 and not privacy_emitted:
                    privacy_emitted = True
                    yield _sse({"type": "privacy"})
                yield _sse({"type": "progress", "processed": processed, "total": total})

            await gather_fut

            entries.sort(key=lambda e: e.hours)
            report = PlatinumReport(
                steam_id=steam_id,
                games=entries,
                total=len(entries),
                platinados=sum(1 for e in entries if e.status == STATUS_PLATINADO),
                incompletos=sum(1 for e in entries if e.status == STATUS_INCOMPLETE),
                nunca_jogados=sum(1 for e in entries if e.status == STATUS_NEVER),
                privado=is_private or stats_private,
            )
            yield _sse({"type": "result", "data": report.model_dump()})

    except ValueError as e:
        yield _sse({"type": "error", "message": str(e)})
    except Exception as e:
        yield _sse({"type": "error", "message": f"Erro interno: {e}"})
