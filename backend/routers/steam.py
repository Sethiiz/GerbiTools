from __future__ import annotations

import os
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from models.steam import PlatinumReport
from services.steam import build_report, build_report_stream

router = APIRouter()


@router.get("/platinum", response_model=PlatinumReport)
async def platinum(profile: str = Query(..., description="SteamID64 ou vanity URL")):
    api_key = os.getenv("STEAM_API_KEY", "").strip()
    if not api_key:
        raise HTTPException(status_code=500, detail="STEAM_API_KEY não configurada no servidor.")
    try:
        return await build_report(api_key, profile)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/platinum/stream")
async def platinum_stream(profile: str = Query(..., description="SteamID64 ou vanity URL")):
    api_key = os.getenv("STEAM_API_KEY", "").strip()
    if not api_key:
        raise HTTPException(status_code=500, detail="STEAM_API_KEY não configurada no servidor.")
    return StreamingResponse(
        build_report_stream(api_key, profile),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
