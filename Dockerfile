FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

COPY . .

RUN rm -rf tools/DeadIslandCollectables tools/SteamPlatViewer \
 && git clone https://github.com/Sethiiz/DeadIslandCollectables.git tools/DeadIslandCollectables \
 && git clone https://github.com/Sethiiz/SteamPlatViewer.git tools/SteamPlatViewer \
 && pip install --no-cache-dir -r backend/requirements.txt

WORKDIR /app/backend

CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
