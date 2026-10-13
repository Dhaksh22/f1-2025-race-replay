from __future__ import annotations

import asyncio
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect

from backend.app.schemas.session import ChatMessage, ChatResponse
from backend.app.services.chatbot import answer_f1_question
from backend.app.services.race_data import (
    SessionUnavailableError,
    get_event_sessions,
    get_replay_frame_chunk,
    get_supporting_years,
    invalidate_processed_cache,
    list_available_events,
    load_replay_payload,
    load_session_details,
    validate_round_number,
    validate_session_type,
)
from backend.app.services.replay import build_leaderboard_snapshot, get_track_status_label
from backend.app.services.telemetry import compare_driver_telemetry
from backend.app.core.config import settings
from src.lib.season import SUPPORTED_SEASON, require_2025_year

router = APIRouter(prefix="/api")


def _validate_2025_or_400(year: int) -> int:
    try:
        return require_2025_year(year)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/health")
def health() -> Dict[str, Any]:
    return {
        "status": "ok",
        "supported_years": get_supporting_years(),
        "season_lock": SUPPORTED_SEASON,
        "llm_configured": settings.is_llm_configured,
        "llm_provider": settings.llm_provider,
    }


@router.get("/seasons")
def list_seasons() -> Dict[str, Any]:
    return {"supported_years": get_supporting_years(), "default_year": SUPPORTED_SEASON}


@router.get("/events")
def get_events(year: int = Query(default=2025)) -> Dict[str, Any]:
    normalized_year = _validate_2025_or_400(year)
    return {"year": normalized_year, "events": list_available_events(normalized_year)}


@router.get("/events/{round_number}/sessions")
def get_sessions_for_event(
    round_number: int, year: int = Query(default=2025)
) -> Dict[str, Any]:
    normalized_year = _validate_2025_or_400(year)
    try:
        return get_event_sessions(round_number=round_number, year=normalized_year)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/sessions/{year}/{round_number}")
def get_session_preview(
    year: int,
    round_number: int,
    session_type: str = Query(default="R"),
) -> Dict[str, Any]:
    normalized_year = _validate_2025_or_400(year)
    try:
        norm_round = validate_round_number(round_number)
        norm_session = validate_session_type(session_type)
        return load_session_details(normalized_year, norm_round, norm_session)
    except SessionUnavailableError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/sessions/{year}/{round_number}/replay")
def get_replay(
    year: int,
    round_number: int,
    session_type: str = Query(default="R"),
    include_frames: bool = Query(default=True),
    refresh: bool = Query(default=False),
) -> Dict[str, Any]:
    normalized_year = _validate_2025_or_400(year)
    try:
        norm_round = validate_round_number(round_number)
        norm_session = validate_session_type(session_type)
        payload = load_replay_payload(
            normalized_year, norm_round, norm_session, refresh=refresh
        )
        if not include_frames:
            summary_copy = dict(payload)
            summary_copy["frames"] = []
            return summary_copy
        return payload
    except SessionUnavailableError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/sessions/{year}/{round_number}/frames")
def get_replay_frames(
    year: int,
    round_number: int,
    session_type: str = Query(default="R"),
    start_frame: int = Query(default=0, ge=0),
    end_frame: Optional[int] = Query(default=None, ge=0),
    step: int = Query(default=1, ge=1, le=50),
) -> Dict[str, Any]:
    normalized_year = _validate_2025_or_400(year)
    try:
        norm_round = validate_round_number(round_number)
        norm_session = validate_session_type(session_type)
        return get_replay_frame_chunk(
            year=normalized_year,
            round_number=norm_round,
            session_type=norm_session,
            start_frame=start_frame,
            end_frame=end_frame,
            step=step,
        )
    except SessionUnavailableError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/sessions/{year}/{round_number}/leaderboard")
def get_session_leaderboard(
    year: int,
    round_number: int,
    session_type: str = Query(default="R"),
    frame_index: int = Query(default=0, ge=0),
    lap: Optional[int] = Query(default=None, ge=1),
) -> Dict[str, Any]:
    normalized_year = _validate_2025_or_400(year)
    try:
        norm_round = validate_round_number(round_number)
        norm_session = validate_session_type(session_type)
        payload = load_replay_payload(normalized_year, norm_round, norm_session)
        frames = payload.get("frames", [])
        target_idx = frame_index
        if lap is not None and frames:
            for idx, f in enumerate(frames):
                if int(f.get("lap", 1)) >= lap:
                    target_idx = idx
                    break
        driver_meta = {
            d["code"]: d for d in payload.get("session", {}).get("drivers", [])
        }
        return build_leaderboard_snapshot(
            frames=frames,
            frame_index=target_idx,
            track_statuses=payload.get("track_statuses", []),
            driver_meta=driver_meta,
            lap_summaries=payload.get("lap_summaries"),
            total_laps=payload.get("session", {}).get("total_laps"),
        )
    except SessionUnavailableError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/sessions/{year}/{round_number}/telemetry")
def get_session_telemetry(
    year: int,
    round_number: int,
    driver: str = Query(..., min_length=2, max_length=5),
    compare_with: Optional[str] = Query(default=None),
    session_type: str = Query(default="R"),
    mode: str = Query(default="lap", pattern="^(lap|time|quali_segment|best_lap)$"),
    lap: Optional[int] = Query(default=None, ge=1),
    start_time: Optional[float] = Query(default=None, ge=0.0),
    end_time: Optional[float] = Query(default=None, ge=0.0),
    segment: Optional[str] = Query(default=None),
) -> Dict[str, Any]:
    normalized_year = _validate_2025_or_400(year)
    try:
        norm_round = validate_round_number(round_number)
        norm_session = validate_session_type(session_type)
        payload = load_replay_payload(normalized_year, norm_round, norm_session)
        return compare_driver_telemetry(
            payload=payload,
            primary_driver=driver,
            compare_driver=compare_with,
            mode=mode,
            lap=lap,
            start_time=start_time,
            end_time=end_time,
            segment=segment,
        )
    except SessionUnavailableError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/sessions/{year}/{round_number}/strategy")
def get_session_strategy(
    year: int,
    round_number: int,
    session_type: str = Query(default="R"),
    driver: Optional[str] = Query(default=None),
) -> Dict[str, Any]:
    normalized_year = _validate_2025_or_400(year)
    try:
        norm_round = validate_round_number(round_number)
        norm_session = validate_session_type(session_type)
        payload = load_replay_payload(normalized_year, norm_round, norm_session)
        strategies = payload.get("strategies", [])
        if driver:
            code = driver.upper().strip()
            strategies = [s for s in strategies if s.get("code") == code]
        return {
            "year": normalized_year,
            "round_number": norm_round,
            "session_type": norm_session,
            "total_laps": payload.get("session", {}).get("total_laps"),
            "strategies": strategies,
        }
    except SessionUnavailableError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/sessions/{year}/{round_number}/laps")
def get_session_laps(
    year: int,
    round_number: int,
    session_type: str = Query(default="R"),
    driver: Optional[str] = Query(default=None),
) -> Dict[str, Any]:
    normalized_year = _validate_2025_or_400(year)
    try:
        norm_round = validate_round_number(round_number)
        norm_session = validate_session_type(session_type)
        payload = load_replay_payload(normalized_year, norm_round, norm_session)
        lap_summaries = payload.get("lap_summaries", {})
        drivers_map = lap_summaries.get("drivers", {})
        if driver:
            code = driver.upper().strip()
            drivers_map = {k: v for k, v in drivers_map.items() if k == code}
        return {
            "year": normalized_year,
            "round_number": norm_round,
            "session_type": norm_session,
            "session_best_sectors": lap_summaries.get("session_best_sectors", {}),
            "status_laps": payload.get("track_status", []),
            "drivers": drivers_map,
        }
    except SessionUnavailableError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/sessions/{year}/{round_number}/race-control")
def get_session_race_control(
    year: int,
    round_number: int,
    session_type: str = Query(default="R"),
    up_to_time: Optional[float] = Query(default=None, ge=0.0),
) -> Dict[str, Any]:
    normalized_year = _validate_2025_or_400(year)
    try:
        norm_round = validate_round_number(round_number)
        norm_session = validate_session_type(session_type)
        payload = load_replay_payload(normalized_year, norm_round, norm_session)
        messages = payload.get("race_control_messages", [])
        if up_to_time is not None:
            messages = [m for m in messages if float(m.get("time", 0.0)) <= up_to_time]
        return {
            "year": normalized_year,
            "round_number": norm_round,
            "session_type": norm_session,
            "track_status_periods": payload.get("track_status", []),
            "race_control_messages": messages,
            "safety_car_note": (
                "Safety Car track coordinates are simulated ahead of the race leader "
                "from official FIA track_status timestamps because official feeds do not "
                "provide GPS telemetry for the Safety Car."
            ),
        }
    except SessionUnavailableError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/sessions/{year}/{round_number}/cache")
def clear_session_cache(
    year: int,
    round_number: int,
    session_type: str = Query(default="R"),
) -> Dict[str, Any]:
    normalized_year = _validate_2025_or_400(year)
    try:
        removed = invalidate_processed_cache(normalized_year, round_number, session_type)
        return {"status": "cleared" if removed else "not_found", "year": normalized_year, "round_number": round_number, "session_type": session_type}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/chat", response_model=ChatResponse)
def post_chat(req: ChatMessage) -> ChatResponse:
    try:
        return answer_f1_question(req)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.websocket("/ws/replay/{year}/{round_number}")
async def websocket_replay_endpoint(
    websocket: WebSocket,
    year: int,
    round_number: int,
    session_type: str = Query(default="R"),
) -> None:
    """
    Incremental WebSocket replay streaming endpoint.
    Supports interactive playback control commands:
      - {"action": "play"}
      - {"action": "pause"}
      - {"action": "seek", "frame_index": <int>}
      - {"action": "set_speed", "speed": <float>}
      - {"action": "reset"}
      - {"action": "ping"}
    """
    await websocket.accept()
    try:
        normalized_year = require_2025_year(year)
        norm_round = validate_round_number(round_number)
        norm_session = validate_session_type(session_type)
        payload = load_replay_payload(normalized_year, norm_round, norm_session)
    except Exception as exc:
        await websocket.send_json({"type": "error", "detail": str(exc)})
        await websocket.close(code=1008)
        return

    frames = payload.get("frames", [])
    total_frames = len(frames)
    track_statuses = payload.get("track_statuses", [])
    driver_meta = {
        d["code"]: d for d in payload.get("session", {}).get("drivers", [])
    }

    current_idx = 0
    playing = False
    speed = 1.0

    def _build_frame_packet(idx: int) -> Dict[str, Any]:
        if not frames:
            return {"type": "frame", "frame_index": 0, "total_frames": 0, "frame": None}
        clamped = max(0, min(idx, total_frames - 1))
        f = dict(frames[clamped])
        f["frame_index"] = clamped
        t = float(f.get("t", 0.0))
        active_code = "1"
        for st in track_statuses:
            s_t = float(st.get("start_time", 0.0))
            e_t = st.get("end_time")
            if t >= s_t and (e_t is None or t < float(e_t)):
                active_code = str(st.get("status", "1"))
                break
        f["track_status"] = active_code
        f["track_status_label"] = get_track_status_label(active_code)
        if f.get("safety_car"):
            sc = dict(f["safety_car"])
            sc["is_simulated"] = True
            f["safety_car"] = sc
        return {
            "type": "frame",
            "frame_index": clamped,
            "total_frames": total_frames,
            "is_paused": not playing,
            "playback_speed": speed,
            "frame": f,
            "leaderboard": build_leaderboard_snapshot(
                frames=frames,
                frame_index=clamped,
                track_statuses=track_statuses,
                driver_meta=driver_meta,
                lap_summaries=payload.get("lap_summaries"),
                total_laps=payload.get("session", {}).get("total_laps"),
            ),
        }

    # Send compact initial session summary + frame 0
    await websocket.send_json(
        {
            "type": "session_init",
            "season": SUPPORTED_SEASON,
            "session": payload["session"],
            "track_geometry": payload["track_geometry"],
            "driver_colors": payload["driver_colors"],
            "track_status": payload["track_status"],
            "timeline_events": payload["timeline_events"],
            "race_control_messages": payload["race_control_messages"],
            "total_frames": total_frames,
            "initial_frame": _build_frame_packet(0),
        }
    )

    try:
        while True:
            timeout_s = max(0.02, min(0.25, 0.08 / max(0.1, speed))) if playing else 30.0
            try:
                cmd = await asyncio.wait_for(websocket.receive_json(), timeout=timeout_s)
                action = str(cmd.get("action", "")).lower().strip()

                if action == "ping":
                    await websocket.send_json({"type": "pong"})
                    continue
                elif action == "play":
                    playing = True
                elif action == "pause":
                    playing = False
                elif action == "reset":
                    playing = False
                    current_idx = 0
                elif action == "seek":
                    target = int(cmd.get("frame_index", 0))
                    current_idx = max(0, min(target, max(0, total_frames - 1)))
                elif action == "set_speed":
                    req_speed = float(cmd.get("speed", 1.0))
                    speed = max(0.1, min(64.0, req_speed))

                await websocket.send_json(_build_frame_packet(current_idx))
            except asyncio.TimeoutError:
                if playing and total_frames > 0:
                    step_frames = max(1, int(round(speed)))
                    if current_idx + step_frames < total_frames:
                        current_idx += step_frames
                        await websocket.send_json(_build_frame_packet(current_idx))
                    else:
                        current_idx = total_frames - 1
                        playing = False
                        await websocket.send_json(_build_frame_packet(current_idx))
    except WebSocketDisconnect:
        return
    except Exception:
        return
