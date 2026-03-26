"""FastAPI 入口。CORS 対応 + 静的ファイル配信 + 全ルーター接続。"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from kawasaki_keiba.api.config import PROJECT_ROOT


def create_app() -> FastAPI:
    # ルーターは関数内で import（循環 import 回避）
    from kawasaki_keiba.api.routes import advisory, dashboard, health, races

    app = FastAPI(
        title="川崎競馬AI Dashboard",
        description="川崎競馬限定 多層意思決定AIシステム",
        version="0.2.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(dashboard.router)
    app.include_router(races.router)
    app.include_router(advisory.router)

    web_dir = PROJECT_ROOT / "web"
    if web_dir.is_dir():
        app.mount("/", StaticFiles(directory=str(web_dir), html=True), name="web")

    return app


app = create_app()
