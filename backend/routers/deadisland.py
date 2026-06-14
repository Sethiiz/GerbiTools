from __future__ import annotations

from fastapi import APIRouter, HTTPException, UploadFile, File
from models.deadisland import CollectableReport
from services.deadisland import process_save_bytes

router = APIRouter()


@router.post("/check", response_model=CollectableReport)
async def check_save(file: UploadFile = File(...)):
    if not file.filename.endswith(".sav"):
        raise HTTPException(status_code=400, detail="Envie um arquivo .sav válido.")
    data = await file.read()
    try:
        return process_save_bytes(data)
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))
