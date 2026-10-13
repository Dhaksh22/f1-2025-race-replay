from __future__ import annotations

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.routes import router, websocket_replay_endpoint
from backend.app.core.config import settings


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version="1.0.0",
        description=(
            "Lightweight web backend for 2025 Formula 1 Race Replay, Telemetry Analytics, "
            "Tyre Strategy, and Grounded F1 Knowledge Chatbot."
        ),
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router)

    @app.get("/", tags=["root"])
    def root() -> dict[str, object]:
        return {
            "service": settings.app_name,
            "version": "1.0.0",
            "supported_season": 2025,
            "docs_url": "/docs",
            "health_url": "/api/health",
        }

    @app.websocket("/ws/replay/{year}/{round_number}")
    async def root_replay_websocket_alias(
        websocket: WebSocket,
        year: int,
        round_number: int,
        session_type: str = "R",
    ) -> None:
        await websocket_replay_endpoint(
            websocket=websocket,
            year=year,
            round_number=round_number,
            session_type=session_type,
        )

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.app.main:app", host=settings.host, port=settings.port, reload=False)
