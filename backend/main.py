import os
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from routers import deadisland, steam

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

app = FastAPI(title="GerbiTools", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(deadisland.router, prefix="/deadisland", tags=["Dead Island"])
app.include_router(steam.router,      prefix="/steam",      tags=["Steam"])

app.mount("/", StaticFiles(directory="../frontend", html=True), name="frontend")
