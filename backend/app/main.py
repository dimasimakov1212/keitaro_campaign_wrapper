# backend/app/main.py

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
import traceback

from app.keitaro.client import keitaro_client

app = FastAPI(title="Keitaro Wrapper")

# Подключаем роуты API (пока пустые)
# from app.api.routes import router
# app.include_router(router, prefix="/api")

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

@app.get("/api/test/keitaro-domains")
async def test_keitaro_domains():
    try:
        domains = await keitaro_client.get_domains()
        return {"success": True, "data": domains}
    except Exception as e:
        # Теперь мы вернем полный стек ошибки, чтобы точно понять, что случилось
        return {
            "success": False, 
            "error": str(e),
            "traceback": traceback.format_exc()
        }
