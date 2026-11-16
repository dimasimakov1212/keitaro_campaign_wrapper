# backend/app/main.py

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
import traceback

from app.keitaro.client import keitaro_client
from app.api.routes import router

app = FastAPI(title="Keitaro Wrapper")

# Подключаем роуты API
app.include_router(router)

# Отдаем статику Vue
static_path = os.path.join(os.path.dirname(__file__), "../static")
if os.path.exists(static_path):
    app.mount("/assets", StaticFiles(directory=os.path.join(static_path, "assets")), name="assets")

    @app.get("/")
    async def serve_spa():
        return FileResponse(os.path.join(static_path, "index.html"))

@app.get("/api/health")
async def health_check():
    return {"status": "ok"}
