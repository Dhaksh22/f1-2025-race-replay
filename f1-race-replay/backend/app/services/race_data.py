from __future__ import annotations

import gzip
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from backend.app.core.config import settings
from backend.app.services.replay import (
    build_leaderboard_snapshot,
    build_track_geometry_from_lap,
    compute_lap_and_sector_summaries,
    compute_status_laps,
    compute_strategy_summaries,
    extract_timeline_events,
    get_track_status_label,
    rgb_tuple_to_hex,
)
from src.f1_data import (
    FPS,
    _get_current_championship_standings,
    enable_cache,
    get_circuit_rotation,
    get_driver_colors,
    get_live_standings,
    get_practice_telemetry,
    get_quali_telemetry,
    get_race_telemetry,
    get_race_weekends_by_year,
    load_session,
)
from src.lib.season import SUPPORTED_SEASON, require_2025_year
from src.lib.tyres import get_tyre_compound_str

VALID_SESSION_TYPES: Dict[str, str] = {
    "R": "Race",
    "S": "Sprint",
    "Q": "Qualifying",
    "SQ": "Sprint Qualifying",
    "FP1": "Practice 1",
    "FP2": "Practice 2",
    "FP3": "Practice 3",
}

# Official 2025 FIA Formula 1 World Championship Calendar (24 Rounds)
FALLBACK_2025_CALENDAR: List[Dict[str, Any]] = [
    {"round_number": 1, "event_name": "Australian Grand Prix", "circuit_name": "Melbourne", "country": "Australia", "date": "2025-03-16", "type": "conventional", "total_laps": 58},
    {"round_number": 2, "event_name": "Chinese Grand Prix", "circuit_name": "Shanghai", "country": "China", "date": "2025-03-23", "type": "sprint_qualifying", "total_laps": 56},
    {"round_number": 3, "event_name": "Japanese Grand Prix", "circuit_name": "Suzuka", "country": "Japan", "date": "2025-04-06", "type": "conventional", "total_laps": 53},
    {"round_number": 4, "event_name": "Bahrain Grand Prix", "circuit_name": "Sakhir", "country": "Bahrain", "date": "2025-04-13", "type": "conventional", "total_laps": 57},
    {"round_number": 5, "event_name": "Saudi Arabian Grand Prix", "circuit_name": "Jeddah", "country": "Saudi Arabia", "date": "2025-04-20", "type": "conventional", "total_laps": 50},
    {"round_number": 6, "event_name": "Miami Grand Prix", "circuit_name": "Miami", "country": "United States", "date": "2025-05-04", "type": "sprint_qualifying", "total_laps": 57},
    {"round_number": 7, "event_name": "Emilia Romagna Grand Prix", "circuit_name": "Imola", "country": "Italy", "date": "2025-05-18", "type": "conventional", "total_laps": 63},
    {"round_number": 8, "event_name": "Monaco Grand Prix", "circuit_name": "Monaco", "country": "Monaco", "date": "2025-05-25", "type": "conventional", "total_laps": 78},
    {"round_number": 9, "event_name": "Spanish Grand Prix", "circuit_name": "Barcelona", "country": "Spain", "date": "2025-06-01", "type": "conventional", "total_laps": 66},
    {"round_number": 10, "event_name": "Canadian Grand Prix", "circuit_name": "Montreal", "country": "Canada", "date": "2025-06-15", "type": "conventional", "total_laps": 70},
    {"round_number": 11, "event_name": "Austrian Grand Prix", "circuit_name": "Spielberg", "country": "Austria", "date": "2025-06-29", "type": "conventional", "total_laps": 71},
    {"round_number": 12, "event_name": "British Grand Prix", "circuit_name": "Silverstone", "country": "United Kingdom", "date": "2025-07-06", "type": "conventional", "total_laps": 52},
    {"round_number": 13, "event_name": "Belgian Grand Prix", "circuit_name": "Spa-Francorchamps", "country": "Belgium", "date": "2025-07-27", "type": "sprint_qualifying", "total_laps": 44},
    {"round_number": 14, "event_name": "Hungarian Grand Prix", "circuit_name": "Budapest", "country": "Hungary", "date": "2025-08-03", "type": "conventional", "total_laps": 70},
    {"round_number": 15, "event_name": "Dutch Grand Prix", "circuit_name": "Zandvoort", "country": "Netherlands", "date": "2025-08-31", "type": "conventional", "total_laps": 72},
    {"round_number": 16, "event_name": "Italian Grand Prix", "circuit_name": "Monza", "country": "Italy", "date": "2025-09-07", "type": "conventional", "total_laps": 53},
    {"round_number": 17, "event_name": "Azerbaijan Grand Prix", "circuit_name": "Baku", "country": "Azerbaijan", "date": "2025-09-21", "type": "conventional", "total_laps": 51},
    {"round_number": 18, "event_name": "Singapore Grand Prix", "circuit_name": "Marina Bay", "country": "Singapore", "date": "2025-10-05", "type": "conventional", "total_laps": 62},
    {"round_number": 19, "event_name": "United States Grand Prix", "circuit_name": "Austin", "country": "United States", "date": "2025-10-19", "type": "sprint_qualifying", "total_laps": 56},
    {"round_number": 20, "event_name": "Mexico City Grand Prix", "circuit_name": "Mexico City", "country": "Mexico", "date": "2025-10-26", "type": "conventional", "total_laps": 71},
    {"round_number": 21, "event_name": "São Paulo Grand Prix", "circuit_name": "Interlagos", "country": "Brazil", "date": "2025-11-09", "type": "sprint_qualifying", "total_laps": 71},
    {"round_number": 22, "event_name": "Las Vegas Grand Prix", "circuit_name": "Las Vegas", "country": "United States", "date": "2025-11-22", "type": "conventional", "total_laps": 50},
    {"round_number": 23, "event_name": "Qatar Grand Prix", "circuit_name": "Lusail", "country": "Qatar", "date": "2025-11-30", "type": "sprint_qualifying", "total_laps": 57},
    {"round_number": 24, "event_name": "Abu Dhabi Grand Prix", "circuit_name": "Yas Marina", "country": "United Arab Emirates", "date": "2025-12-07", "type": "conventional", "total_laps": 58},
]

DRIVER_ROSTER_2025: List[Dict[str, str]] = [
    {"code": "NOR", "driver_number": "4", "full_name": "Lando Norris", "team": "McLaren", "color": "#FF8000"},
    {"code": "VER", "driver_number": "1", "full_name": "Max Verstappen", "team": "Red Bull Racing", "color": "#3671C6"},
    {"code": "PIA", "driver_number": "81", "full_name": "Oscar Piastri", "team": "McLaren", "color": "#FF8000"},
    {"code": "LEC", "driver_number": "16", "full_name": "Charles Leclerc", "team": "Ferrari", "color": "#E80020"},
    {"code": "RUS", "driver_number": "63", "full_name": "George Russell", "team": "Mercedes", "color": "#27F4D2"},
    {"code": "HAM", "driver_number": "44", "full_name": "Lewis Hamilton", "team": "Ferrari", "color": "#E80020"},
    {"code": "ANT", "driver_number": "12", "full_name": "Kimi Antonelli", "team": "Mercedes", "color": "#27F4D2"},
    {"code": "ALB", "driver_number": "23", "full_name": "Alex Albon", "team": "Williams", "color": "#64C4FF"},
    {"code": "SAI", "driver_number": "55", "full_name": "Carlos Sainz", "team": "Williams", "color": "#64C4FF"},
    {"code": "ALO", "driver_number": "14", "full_name": "Fernando Alonso", "team": "Aston Martin", "color": "#229971"},
    {"code": "GAS", "driver_number": "10", "full_name": "Pierre Gasly", "team": "Alpine", "color": "#FF87BC"},
    {"code": "TSU", "driver_number": "22", "full_name": "Yuki Tsunoda", "team": "Red Bull Racing", "color": "#3671C6"},
    {"code": "OCO", "driver_number": "31", "full_name": "Esteban Ocon", "team": "Haas F1 Team", "color": "#B6BABD"},
    {"code": "BEA", "driver_number": "87", "full_name": "Oliver Bearman", "team": "Haas F1 Team", "color": "#B6BABD"},
    {"code": "HUL", "driver_number": "27", "full_name": "Nico Hülkenberg", "team": "Kick Sauber", "color": "#52E252"},
    {"code": "HAD", "driver_number": "6", "full_name": "Isack Hadjar", "team": "Racing Bulls", "color": "#6692FF"},
    {"code": "STR", "driver_number": "18", "full_name": "Lance Stroll", "team": "Aston Martin", "color": "#229971"},
    {"code": "LAW", "driver_number": "30", "full_name": "Liam Lawson", "team": "Racing Bulls", "color": "#6692FF"},
    {"code": "DOO", "driver_number": "7", "full_name": "Jack Doohan", "team": "Alpine", "color": "#FF87BC"},
    {"code": "BOR", "driver_number": "5", "full_name": "Gabriel Bortoleto", "team": "Kick Sauber", "color": "#52E252"},
]


class SessionUnavailableError(ValueError):
    """Raised when a requested 2025 session has no available telemetry data."""


_MEMORY_CACHE: Dict[str, Dict[str, Any]] = {}


def get_supporting_years() -> List[int]:
    return [SUPPORTED_SEASON]


def validate_session_type(session_type: str) -> str:
    norm = str(session_type or "R").upper().strip()
    if norm not in VALID_SESSION_TYPES:
        raise ValueError(
            f"Unsupported session_type '{session_type}'. Valid types: {', '.join(VALID_SESSION_TYPES.keys())}"
        )
    return norm


def validate_round_number(round_number: int) -> int:
    try:
        r = int(round_number)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Round number must be an integer, received: {round_number!r}") from exc
    if r < 1 or r > 24:
        raise ValueError(f"Round number for 2025 must be between 1 and 24 (received {r}).")
    return r


def get_processed_cache_path(year: int, round_number: int, session_type: str) -> Path:
    normalized_year = require_2025_year(year)
    norm_round = validate_round_number(round_number)
    norm_session = validate_session_type(session_type)
    settings.processed_data_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{settings.cache_version}_{normalized_year}_R{norm_round:02d}_{norm_session}.json.gz"
    return settings.processed_data_dir / filename


def invalidate_processed_cache(year: int, round_number: int, session_type: str) -> bool:
    normalized_year = require_2025_year(year)
    norm_round = validate_round_number(round_number)
    norm_session = validate_session_type(session_type)
    key = f"{normalized_year}_{norm_round}_{norm_session}"
    _MEMORY_CACHE.pop(key, None)
    path = get_processed_cache_path(normalized_year, norm_round, norm_session)
    if path.exists():
        path.unlink()
        return True
    return False


def _sessions_for_format(event_format: str, session_dates: Optional[Dict[str, str]] = None) -> Tuple[List[str], List[Dict[str, Any]]]:
    session_dates = session_dates or {}
    fmt = (event_format or "conventional").lower()
    if "sprint" in fmt:
        codes = ["FP1", "SQ", "S", "Q", "R"]
    else:
        codes = ["FP1", "FP2", "FP3", "Q", "R"]

    name_to_date = {k.lower(): v for k, v in session_dates.items()}
    options = []
    for code in codes:
        human_name = VALID_SESSION_TYPES[code]
        sched_date = (
            name_to_date.get(human_name.lower())
            or name_to_date.get(code.lower())
            or None
        )
        options.append(
            {
                "code": code,
                "session_type": code,
                "name": human_name,
                "label": f"{human_name} ({code})",
                "available": True,
                "scheduled_date": sched_date,
            }
        )
    return codes, options


def list_available_events(year: int = 2025) -> List[Dict[str, Any]]:
    normalized_year = require_2025_year(year)
    fallback_by_round = {item["round_number"]: item for item in FALLBACK_2025_CALENDAR}

    raw_weekends: List[Dict[str, Any]] = []
    if settings.prefer_live_fastf1:
        try:
            raw_weekends = get_race_weekends_by_year(normalized_year) or []
        except Exception as exc:
            print(f"Warning: FastF1 schedule lookup failed, using 2025 calendar metadata: {exc}")

    events_source = raw_weekends if raw_weekends else FALLBACK_2025_CALENDAR
    events: List[Dict[str, Any]] = []

    for idx, item in enumerate(events_source, start=1):
        if isinstance(item, dict):
            r_num = int(item.get("round_number", idx))
            if r_num <= 0:
                continue
            fb = fallback_by_round.get(r_num, {})
            ev_name = str(item.get("event_name") or item.get("EventName") or fb.get("event_name", f"Round {r_num}"))
            circuit_name = str(item.get("circuit_name") or item.get("CircuitName") or fb.get("circuit_name") or ev_name.replace("Grand Prix", "").strip())
            country = str(item.get("country") or fb.get("country") or "")
            date_str = str(item.get("date") or fb.get("date") or "")
            ev_format = str(item.get("type") or fb.get("type") or "conventional")
            s_dates = item.get("session_dates") if isinstance(item.get("session_dates"), dict) else {}
        else:
            r_num = idx
            fb = fallback_by_round.get(r_num, {})
            ev_name = str(item)
            circuit_name = fb.get("circuit_name") or ev_name
            country = fb.get("country", "")
            date_str = fb.get("date", "")
            ev_format = fb.get("type", "conventional")
            s_dates = {}

        codes, session_opts = _sessions_for_format(ev_format, s_dates)
        has_cached = any(
            get_processed_cache_path(normalized_year, r_num, c).exists()
            for c in codes
        )
        events.append(
            {
                "year": normalized_year,
                "round_number": r_num,
                "event_name": ev_name,
                "circuit_name": circuit_name,
                "location": circuit_name,
                "country": country,
                "date": date_str,
                "event_date": date_str,
                "event_format": ev_format,
                "is_sprint_weekend": "sprint" in ev_format.lower(),
                "session_types": codes,
                "sessions": session_opts,
                "has_cached_data": has_cached,
            }
        )

    return events


def get_event_sessions(round_number: int, year: int = 2025) -> Dict[str, Any]:
    normalized_year = require_2025_year(year)
    norm_round = validate_round_number(round_number)
    events = list_available_events(normalized_year)
    matched = next((e for e in events if e["round_number"] == norm_round), None)
    if matched is None:
        raise ValueError(f"Round {norm_round} not found in {normalized_year} season.")
    return matched


def load_session_details(
    year: int,
    round_number: int,
    session_type: str = "R",
    allow_demo_fallback: Optional[bool] = None,
) -> Dict[str, Any]:
    normalized_year = require_2025_year(year)
    norm_round = validate_round_number(round_number)
    norm_session = validate_session_type(session_type)
    use_fallback = settings.allow_demo_fallback if allow_demo_fallback is None else allow_demo_fallback

    cache_key = f"{normalized_year}_{norm_round}_{norm_session}"
    if cache_key in _MEMORY_CACHE:
        return _MEMORY_CACHE[cache_key]["session"]

    cache_file = get_processed_cache_path(normalized_year, norm_round, norm_session)
    if cache_file.exists():
        try:
            with gzip.open(cache_file, "rt", encoding="utf-8") as f:
                cached_payload = json.load(f)
            cached_payload["session"]["data_source"] = "cached"
            _MEMORY_CACHE[cache_key] = cached_payload
            return cached_payload["session"]
        except Exception as exc:
            print(f"Warning: failed to read processed cache {cache_file}: {exc}")

    session = load_session(normalized_year, norm_round, norm_session) if settings.prefer_live_fastf1 else None
    if session is None:
        if use_fallback:
            demo_payload = _build_demo_2025_payload(normalized_year, norm_round, norm_session)
            try:
                with gzip.open(cache_file, "wt", encoding="utf-8") as f:
                    json.dump(demo_payload, f)
            except Exception:
                pass
            _MEMORY_CACHE[cache_key] = demo_payload
            return demo_payload["session"]
        raise SessionUnavailableError(
            f"Unable to load session '{norm_session}' for {normalized_year} round {norm_round}."
        )

    fb_event = next(
        (e for e in FALLBACK_2025_CALENDAR if e["round_number"] == norm_round),
        {},
    )
    event_obj = getattr(session, "event", None)
    event_name = (
        event_obj.get("EventName", fb_event.get("event_name", f"Round {norm_round}"))
        if event_obj is not None and hasattr(event_obj, "get")
        else fb_event.get("event_name", f"Round {norm_round}")
    )
    circuit_name = (
        event_obj.get("Location", fb_event.get("circuit_name", ""))
        if event_obj is not None and hasattr(event_obj, "get")
        else fb_event.get("circuit_name", "")
    )
    country = (
        event_obj.get("Country", fb_event.get("country", ""))
        if event_obj is not None and hasattr(event_obj, "get")
        else fb_event.get("country", "")
    )
    ev_date = (
        event_obj.get("EventDate")
        if event_obj is not None and hasattr(event_obj, "get")
        else None
    )
    date_str = (
        ev_date.strftime("%Y-%m-%d")
        if hasattr(ev_date, "strftime")
        else fb_event.get("date", "2025")
    )
    total_laps = getattr(session, "total_laps", None) or fb_event.get("total_laps")

    try:
        raw_colors = get_driver_colors(session)
    except Exception:
        raw_colors = {}

    drivers_list: List[Dict[str, Any]] = []
    for drv_id in getattr(session, "drivers", []):
        drv_obj = session.get_driver(drv_id) if hasattr(session, "get_driver") else None
        if isinstance(drv_obj, dict) or hasattr(drv_obj, "get"):
            code = str(drv_obj.get("Abbreviation") or drv_id)
            team = drv_obj.get("TeamName")
            full_name = drv_obj.get("FullName") or code
            drv_num = str(drv_obj.get("DriverNumber") or drv_id)
        else:
            code = str(drv_id)
            team = getattr(drv_obj, "TeamName", None)
            full_name = getattr(drv_obj, "FullName", code)
            drv_num = str(drv_id)

        color_hex = rgb_tuple_to_hex(raw_colors.get(code), "#FFFFFF")
        drivers_list.append(
            {
                "code": code,
                "driver_number": drv_num,
                "full_name": full_name,
                "team": team,
                "color": color_hex,
            }
        )

    try:
        rotation = float(get_circuit_rotation(session) or 0.0)
    except Exception:
        rotation = 0.0

    return {
        "year": normalized_year,
        "round_number": norm_round,
        "session_type": norm_session,
        "event_name": str(event_name),
        "circuit_name": str(circuit_name),
        "country": str(country),
        "date": str(date_str),
        "total_laps": int(total_laps) if isinstance(total_laps, (int, float)) else None,
        "circuit_length_m": None,
        "circuit_rotation": rotation,
        "fps": FPS,
        "total_frames": 0,
        "duration_s": 0.0,
        "drivers": drivers_list,
        "status": "ready",
        "data_source": "fastf1",
        "notice": None,
    }


def load_replay_payload(
    year: int,
    round_number: int,
    session_type: str = "R",
    refresh: bool = False,
    allow_demo_fallback: Optional[bool] = None,
) -> Dict[str, Any]:
    """
    Load or compute the complete serializable 2025 session replay payload.
    Reuses processed cache when available unless refresh=True.
    """
    normalized_year = require_2025_year(year)
    norm_round = validate_round_number(round_number)
    norm_session = validate_session_type(session_type)
    use_fallback = settings.allow_demo_fallback if allow_demo_fallback is None else allow_demo_fallback

    cache_key = f"{normalized_year}_{norm_round}_{norm_session}"
    cache_file = get_processed_cache_path(normalized_year, norm_round, norm_session)

    if refresh:
        invalidate_processed_cache(normalized_year, norm_round, norm_session)
    else:
        if cache_key in _MEMORY_CACHE:
            return _MEMORY_CACHE[cache_key]
        if cache_file.exists():
            try:
                with gzip.open(cache_file, "rt", encoding="utf-8") as f:
                    cached_payload = json.load(f)
                cached_payload["session"]["data_source"] = "cached"
                _MEMORY_CACHE[cache_key] = cached_payload
                return cached_payload
            except Exception as exc:
                print(f"Warning: corrupted cache {cache_file}, recomputing: {exc}")

    try:
        enable_cache()
    except Exception:
        pass

    session = load_session(normalized_year, norm_round, norm_session) if settings.prefer_live_fastf1 else None
    if session is None:
        if use_fallback:
            demo_payload = _build_demo_2025_payload(normalized_year, norm_round, norm_session)
            try:
                with gzip.open(cache_file, "wt", encoding="utf-8") as f:
                    json.dump(demo_payload, f)
            except Exception:
                pass
            _MEMORY_CACHE[cache_key] = demo_payload
            return demo_payload
        raise SessionUnavailableError(
            f"Unable to load session '{norm_session}' for {normalized_year} round {norm_round}."
        )

    session_meta = load_session_details(
        normalized_year, norm_round, norm_session, allow_demo_fallback=False
    )

    # Extract telemetry & frames using existing src/f1_data.py functions
    frames: List[Dict[str, Any]] = []
    track_statuses: List[Dict[str, Any]] = []
    race_control_messages: List[Dict[str, Any]] = []
    quali_practice_telemetry: Dict[str, Any] = {}
    driver_colors: Dict[str, Any] = {
        d["code"]: d.get("color", "#FFFFFF") for d in session_meta.get("drivers", [])
    }

    try:
        if norm_session in ("Q", "SQ"):
            q_data = get_quali_telemetry(session, session_type=norm_session)
            quali_practice_telemetry = q_data.get("telemetry", {})
            results = q_data.get("results", [])
            if results:
                first_code = results[0]["code"]
                drv_q = quali_practice_telemetry.get(first_code, {})
                for seg in ("Q3", "Q2", "Q1"):
                    seg_frames = drv_q.get(seg, {}).get("frames", [])
                    if seg_frames:
                        frames = _convert_single_car_frames_to_multi(
                            seg_frames, quali_practice_telemetry, seg, results
                        )
                        track_statuses = drv_q.get(seg, {}).get("track_statuses", [])
                        break
        elif norm_session in ("FP1", "FP2", "FP3"):
            p_data = get_practice_telemetry(session, session_type=norm_session)
            quali_practice_telemetry = p_data.get("telemetry", {})
            results = p_data.get("results", [])
            if results:
                frames = _convert_practice_frames_to_multi(quali_practice_telemetry, results)
        else:
            race_tel = get_race_telemetry(session, session_type=norm_session)
            frames = race_tel.get("frames", [])
            track_statuses = race_tel.get("track_statuses", [])
            race_control_messages = race_tel.get("race_control_messages", [])
            if race_tel.get("total_laps"):
                session_meta["total_laps"] = int(race_tel["total_laps"])
            if race_tel.get("driver_colors"):
                for c, rgb in race_tel["driver_colors"].items():
                    driver_colors[c] = rgb_tuple_to_hex(rgb, "#FFFFFF")
    except Exception as exc:
        print(f"Warning: FastF1 telemetry extraction failed ({exc})")
        if use_fallback:
            demo_payload = _build_demo_2025_payload(normalized_year, norm_round, norm_session)
            _MEMORY_CACHE[cache_key] = demo_payload
            return demo_payload
        raise SessionUnavailableError(f"Telemetry unavailable for {normalized_year} R{norm_round} {norm_session}: {exc}") from exc

    # Extract representative example lap for track geometry
    example_lap = None
    try:
        if hasattr(session, "laps") and session.laps is not None and len(session.laps) > 0:
            fastest = session.laps.pick_fastest()
            if fastest is not None:
                example_lap = fastest.get_telemetry()
    except Exception:
        example_lap = None

    if example_lap is None and frames:
        # Reconstruct track outline from the first driver's frame coordinates
        first_drv = next(iter(frames[0].get("drivers", {}).keys()), None)
        if first_drv:
            xs = [f["drivers"][first_drv]["x"] for f in frames if first_drv in f.get("drivers", {})]
            ys = [f["drivers"][first_drv]["y"] for f in frames if first_drv in f.get("drivers", {})]
            drs_arr = [f["drivers"][first_drv].get("drs", 0) for f in frames if first_drv in f.get("drivers", {})]
            example_lap = {"X": xs, "Y": ys, "DRS": drs_arr}

    track_geometry = build_track_geometry_from_lap(
        example_lap, rotation_deg=session_meta.get("circuit_rotation", 0.0)
    )
    session_meta["circuit_length_m"] = track_geometry.get("circuit_length_m")
    session_meta["total_frames"] = len(frames)
    session_meta["duration_s"] = round(float(frames[-1]["t"]), 3) if frames else 0.0

    # Normalize driver colors in session_meta
    for drv in session_meta["drivers"]:
        drv["color"] = rgb_tuple_to_hex(
            driver_colors.get(drv["code"], drv.get("color", "#FFFFFF"))
        )

    driver_meta_map = {d["code"]: d for d in session_meta["drivers"]}
    lap_summaries = compute_lap_and_sector_summaries(frames, session=session, driver_colors=driver_colors)
    status_laps = compute_status_laps(frames, track_statuses)
    timeline_events = extract_timeline_events(
        frames, track_statuses, total_laps=session_meta.get("total_laps") or 0
    )
    strategies = compute_strategy_summaries(
        frames=frames,
        lap_summaries=lap_summaries,
        session=session,
        driver_colors=driver_colors,
        total_laps=session_meta.get("total_laps") or 0,
    )

    # Compute live championship standings if race
    live_driver_standings: Dict[str, Any] = {}
    live_constructor_standings: Dict[str, Any] = {}
    if norm_session == "R" and hasattr(session, "laps"):
        try:
            cur_d, cur_c = _get_current_championship_standings(session)
            live_d, live_c = get_live_standings(cur_d, cur_c, session)
            live_driver_standings = {str(k): v for k, v in (live_d or {}).items()}
            live_constructor_standings = {str(k): v for k, v in (live_c or {}).items()}
        except Exception:
            pass

    initial_leaderboard = build_leaderboard_snapshot(
        frames=frames,
        frame_index=0,
        track_statuses=track_statuses,
        driver_meta=driver_meta_map,
        lap_summaries=lap_summaries,
        total_laps=session_meta.get("total_laps"),
    )

    payload: Dict[str, Any] = {
        "season": SUPPORTED_SEASON,
        "session": session_meta,
        "track_geometry": track_geometry,
        "driver_colors": driver_colors,
        "track_status": status_laps or track_statuses,
        "track_statuses": track_statuses,
        "race_control_messages": race_control_messages,
        "timeline_events": timeline_events,
        "lap_summaries": lap_summaries,
        "strategies": strategies,
        "leaderboard": [initial_leaderboard],
        "live_driver_standings": live_driver_standings,
        "live_constructor_standings": live_constructor_standings,
        "frames": frames,
    }
    if quali_practice_telemetry:
        payload["quali_practice_telemetry"] = quali_practice_telemetry

    # Persist to versioned compressed processed cache when derived from real FastF1 session
    if session_meta.get("data_source") == "fastf1" and frames:
        try:
            with gzip.open(cache_file, "wt", encoding="utf-8") as f:
                json.dump(payload, f)
        except Exception as exc:
            print(f"Warning: could not write processed cache {cache_file}: {exc}")

    _MEMORY_CACHE[cache_key] = payload
    return payload


def get_replay_frame_chunk(
    year: int,
    round_number: int,
    session_type: str = "R",
    start_frame: int = 0,
    end_frame: Optional[int] = None,
    step: int = 1,
) -> Dict[str, Any]:
    """
    Return a bounded slice of replay frames for incremental HTTP loading or seeking.
    """
    payload = load_replay_payload(year, round_number, session_type)
    all_frames = payload.get("frames", [])
    total = len(all_frames)
    step = max(1, int(step))
    start_idx = max(0, min(int(start_frame), max(0, total - 1)))
    end_idx = (
        min(total, int(end_frame))
        if end_frame is not None
        else min(total, start_idx + 250)
    )
    track_statuses = payload.get("track_statuses", [])

    sliced: List[Dict[str, Any]] = []
    for idx in range(start_idx, end_idx, step):
        f = dict(all_frames[idx])
        f["frame_index"] = idx
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
        sliced.append(f)

    return {
        "year": SUPPORTED_SEASON,
        "round_number": int(round_number),
        "session_type": validate_session_type(session_type),
        "start_frame": start_idx,
        "end_frame": end_idx,
        "step": step,
        "total_frames": total,
        "frames": sliced,
    }


def _convert_single_car_frames_to_multi(
    seg_frames: List[Dict[str, Any]],
    quali_telemetry: Dict[str, Any],
    segment: str,
    results: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Adapt Qualifying per-driver segment frames into unified multi-driver replay frames."""
    max_len = len(seg_frames)
    multi_frames: List[Dict[str, Any]] = []
    pos_map = {r["code"]: r.get("position", idx + 1) for idx, r in enumerate(results)}

    for i in range(max_len):
        t = float(seg_frames[i].get("t", i * 0.04))
        drv_dict: Dict[str, Any] = {}
        for code, d_store in quali_telemetry.items():
            s_data = d_store.get(segment, {})
            f_list = s_data.get("frames", [])
            if not f_list:
                continue
            f_item = f_list[min(i, len(f_list) - 1)]
            tel = f_item.get("telemetry", {})
            comp = int(s_data.get("compound", 0))
            drv_dict[code] = {
                "x": float(tel.get("x", 0.0)),
                "y": float(tel.get("y", 0.0)),
                "dist": float(tel.get("dist", 0.0)),
                "rel_dist": float(tel.get("rel_dist", 0.0)),
                "lap": 1,
                "position": int(pos_map.get(code, 1)),
                "tyre": comp,
                "tyre_life": 2,
                "speed": float(tel.get("speed", 0.0)),
                "gear": int(tel.get("gear", 0)),
                "drs": int(tel.get("drs", 0)),
                "throttle": float(tel.get("throttle", 0.0)),
                "brake": float(tel.get("brake", 0.0)) / 100.0,
                "in_pit": False,
            }
        multi_frames.append({"t": round(t, 3), "lap": 1, "drivers": drv_dict})
    return multi_frames


def _convert_practice_frames_to_multi(
    practice_telemetry: Dict[str, Any], results: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    pos_map = {r["code"]: r.get("position", idx + 1) for idx, r in enumerate(results)}
    first_code = results[0]["code"] if results else None
    if not first_code or first_code not in practice_telemetry:
        return []
    base_frames = practice_telemetry[first_code].get("best_lap", {}).get("frames", [])
    multi_frames: List[Dict[str, Any]] = []
    for i, bf in enumerate(base_frames):
        t = float(bf.get("t", i * 0.04))
        drv_dict: Dict[str, Any] = {}
        for code, d_store in practice_telemetry.items():
            f_list = d_store.get("best_lap", {}).get("frames", [])
            if not f_list:
                continue
            f_item = f_list[min(i, len(f_list) - 1)]
            tel = f_item.get("telemetry", {})
            drv_dict[code] = {
                "x": float(tel.get("x", 0.0)),
                "y": float(tel.get("y", 0.0)),
                "dist": float(tel.get("dist", 0.0)),
                "rel_dist": float(tel.get("rel_dist", 0.0)),
                "lap": 1,
                "position": int(pos_map.get(code, 1)),
                "tyre": 1,
                "tyre_life": 3,
                "speed": float(tel.get("speed", 0.0)),
                "gear": int(tel.get("gear", 0)),
                "drs": int(tel.get("drs", 0)),
                "throttle": float(tel.get("throttle", 0.0)),
                "brake": float(tel.get("brake", 0.0)) / 100.0,
                "in_pit": False,
            }
        multi_frames.append({"t": round(t, 3), "lap": 1, "drivers": drv_dict})
    return multi_frames


def _build_demo_2025_payload(
    year: int, round_number: int, session_type: str = "R"
) -> Dict[str, Any]:
    """
    Deterministic, clearly labeled 2025 fallback dataset used ONLY when FastF1
    live network/cache is unavailable and ALLOW_DEMO_FALLBACK is enabled.
    """
    ev = next(
        (e for e in FALLBACK_2025_CALENDAR if e["round_number"] == round_number),
        FALLBACK_2025_CALENDAR[0],
    )
    total_laps = 15 if session_type == "S" else (3 if session_type in ("Q", "SQ", "FP1", "FP2", "FP3") else 20)
    circuit_len = 5278.0 + (round_number * 37.0)

    # Parametric F1 circuit shape (multi-harmonic closed loop)
    n_pts = 240
    theta = np.linspace(0, 2 * np.pi, n_pts, endpoint=False)
    phase_shift = (round_number % 7) * 0.35
    r = (
        3200.0
        + 950.0 * np.cos(2 * theta + phase_shift)
        + 520.0 * np.sin(3 * theta - phase_shift)
        + 280.0 * np.cos(5 * theta)
    )
    x_track = r * np.cos(theta) * 1.35
    y_track = r * np.sin(theta) * 0.85
    drs_arr = np.where(
        ((theta > 0.15) & (theta < 0.85)) | ((theta > 3.3) & (theta < 4.05)),
        12,
        0,
    )
    curvature = np.abs(np.gradient(np.gradient(x_track))) + np.abs(
        np.gradient(np.gradient(y_track))
    )
    curv_norm = (curvature - curvature.min()) / (curvature.max() - curvature.min() + 1e-6)

    example_lap = {
        "X": x_track,
        "Y": y_track,
        "DRS": drs_arr,
        "Distance": np.linspace(0, circuit_len, n_pts),
    }
    rotation_deg = float((round_number * 15) % 360)
    track_geometry = build_track_geometry_from_lap(
        example_lap, rotation_deg=rotation_deg, track_width=220.0
    )

    drivers_info = [dict(d) for d in DRIVER_ROSTER_2025]
    driver_colors = {d["code"]: d["color"] for d in drivers_info}

    # Build 300 frames covering total_laps (with realistic speed, gear, throttle, brake, pit stop, and Safety Car period)
    num_frames = 300
    base_lap_time = 82.5
    total_time = total_laps * base_lap_time
    timeline = np.linspace(0.0, total_time, num_frames)

    sc_start_t = total_time * 0.42
    sc_end_t = total_time * 0.56
    vsc_start_t = total_time * 0.76
    vsc_end_t = total_time * 0.82

    track_statuses = [
        {"status": "1", "start_time": 0.0, "end_time": round(sc_start_t, 2)},
        {"status": "4", "start_time": round(sc_start_t, 2), "end_time": round(sc_end_t, 2)},
        {"status": "1", "start_time": round(sc_end_t, 2), "end_time": round(vsc_start_t, 2)},
        {"status": "6", "start_time": round(vsc_start_t, 2), "end_time": round(vsc_end_t, 2)},
        {"status": "1", "start_time": round(vsc_end_t, 2), "end_time": None},
    ]

    race_control_messages = [
        {"time": 2.0, "category": "Flag", "message": "GREEN LIGHT - PIT EXIT OPEN", "flag": "GREEN", "scope": "Track", "sector": "", "racing_number": ""},
        {"time": 180.0, "category": "Drs", "message": "DRS ENABLED", "flag": "", "scope": "Track", "sector": "", "racing_number": ""},
        {"time": round(sc_start_t - 8.0, 2), "category": "Flag", "message": "YELLOW IN TRACK SECTOR 2", "flag": "YELLOW", "scope": "Sector", "sector": "2", "racing_number": ""},
        {"time": round(sc_start_t, 2), "category": "SafetyCar", "message": "SAFETY CAR DEPLOYED", "flag": "SC", "scope": "Track", "sector": "", "racing_number": ""},
        {"time": round(sc_end_t - 15.0, 2), "category": "SafetyCar", "message": "SAFETY CAR IN THIS LAP", "flag": "SC", "scope": "Track", "sector": "", "racing_number": ""},
        {"time": round(sc_end_t, 2), "category": "Flag", "message": "TRACK CLEAR - GREEN FLAG", "flag": "GREEN", "scope": "Track", "sector": "", "racing_number": ""},
        {"time": round(vsc_start_t, 2), "category": "SafetyCar", "message": "VIRTUAL SAFETY CAR DEPLOYED", "flag": "VSC", "scope": "Track", "sector": "", "racing_number": ""},
        {"time": round(vsc_end_t, 2), "category": "Flag", "message": "VSC ENDING - GREEN FLAG", "flag": "GREEN", "scope": "Track", "sector": "", "racing_number": ""},
    ]

    frames: List[Dict[str, Any]] = []
    for fi, t_val in enumerate(timeline):
        snapshot: List[Dict[str, Any]] = []
        is_sc = sc_start_t <= t_val < sc_end_t
        is_vsc = vsc_start_t <= t_val < vsc_end_t

        for rank_idx, d_meta in enumerate(drivers_info):
            code = d_meta["code"]
            pace_factor = 1.0 - (rank_idx * 0.0022)
            effective_progress_laps = (t_val / base_lap_time) * pace_factor - (rank_idx * 0.012)
            effective_progress_laps = max(0.0, effective_progress_laps)

            lap_num = min(total_laps, int(math.floor(effective_progress_laps)) + 1)
            rel_dist = float(effective_progress_laps % 1.0)
            dist_m = float(effective_progress_laps * circuit_len)

            pt_idx = int(rel_dist * n_pts) % n_pts
            next_idx = (pt_idx + 1) % n_pts
            sub_frac = (rel_dist * n_pts) - int(rel_dist * n_pts)
            wx = float(x_track[pt_idx] * (1.0 - sub_frac) + x_track[next_idx] * sub_frac)
            wy = float(y_track[pt_idx] * (1.0 - sub_frac) + y_track[next_idx] * sub_frac)

            c_val = float(curv_norm[pt_idx])
            base_speed = 328.0 - c_val * 195.0 - rank_idx * 0.5
            if is_sc:
                base_speed = min(base_speed, 195.0)
            elif is_vsc:
                base_speed = min(base_speed, 225.0)

            drs_active = int(drs_arr[pt_idx]) if (not is_sc and not is_vsc and lap_num >= 2 and rank_idx > 0) else 0
            if drs_active >= 10:
                base_speed += 14.0

            gear = max(2, min(8, int(round(base_speed / 41.0))))
            throttle = round(max(5.0, min(100.0, 100.0 - c_val * 92.0)), 1)
            brake = round(max(0.0, min(1.0, (c_val - 0.35) * 1.5)), 2)

            pit_lap = 8 + (rank_idx % 4)
            in_pit = (lap_num == pit_lap) and (rel_dist < 0.08 or rel_dist > 0.94)
            if lap_num <= pit_lap:
                tyre_int = 1 if rank_idx % 2 == 0 else 0  # MEDIUM or SOFT
                tyre_life = lap_num
            else:
                tyre_int = 2  # HARD
                tyre_life = lap_num - pit_lap

            snapshot.append(
                {
                    "code": code,
                    "x": round(wx, 2),
                    "y": round(wy, 2),
                    "dist": round(dist_m, 1),
                    "rel_dist": round(rel_dist, 4),
                    "fraction": round(rel_dist, 4),
                    "lap": int(lap_num),
                    "tyre": int(tyre_int),
                    "tyre_compound_name": get_tyre_compound_str(tyre_int),
                    "tyre_life": int(tyre_life),
                    "speed": round(base_speed, 1),
                    "gear": int(gear),
                    "drs": int(drs_active),
                    "throttle": throttle,
                    "brake": brake,
                    "in_pit": bool(in_pit),
                    "is_out": False,
                }
            )

        snapshot.sort(key=lambda r: (r["lap"], r["dist"]), reverse=True)
        leader_lap = snapshot[0]["lap"] if snapshot else 1
        frame_drivers: Dict[str, Any] = {}
        for pos_idx, car in enumerate(snapshot, start=1):
            c = car["code"]
            car_copy = dict(car)
            car_copy["position"] = pos_idx
            frame_drivers[c] = car_copy

        sc_payload = None
        if is_sc and snapshot:
            leader_rel = snapshot[0]["rel_dist"]
            sc_rel = (leader_rel + 0.035) % 1.0
            sc_idx = int(sc_rel * n_pts) % n_pts
            sc_elapsed = t_val - sc_start_t
            sc_rem = sc_end_t - t_val
            if sc_elapsed < 12.0:
                sc_phase = "deploying"
                sc_alpha = round(min(1.0, max(0.3, sc_elapsed / 12.0)), 2)
            elif sc_rem < 12.0:
                sc_phase = "returning"
                sc_alpha = round(min(1.0, max(0.3, sc_rem / 12.0)), 2)
            else:
                sc_phase = "on_track"
                sc_alpha = 1.0
            sc_payload = {
                "x": round(float(x_track[sc_idx]), 2),
                "y": round(float(y_track[sc_idx]), 2),
                "phase": sc_phase,
                "alpha": sc_alpha,
                "is_simulated": True,
            }

        frames.append(
            {
                "frame_index": fi,
                "t": round(float(t_val), 3),
                "lap": int(leader_lap),
                "track_status": "4" if is_sc else ("6" if is_vsc else "1"),
                "track_status_label": "SC" if is_sc else ("VSC" if is_vsc else "GREEN"),
                "drivers": frame_drivers,
                "weather": {
                    "track_temp": round(34.5 + math.sin(fi / 50.0) * 1.8, 1),
                    "air_temp": round(24.2 + math.cos(fi / 60.0) * 0.7, 1),
                    "humidity": 48.0,
                    "wind_speed": 11.4,
                    "wind_direction": 215.0,
                    "rain_state": "DRY",
                },
                "safety_car": sc_payload,
            }
        )

    session_meta = {
        "year": year,
        "round_number": round_number,
        "session_type": session_type,
        "event_name": ev["event_name"],
        "circuit_name": ev["circuit_name"],
        "country": ev["country"],
        "date": ev["date"],
        "total_laps": total_laps,
        "circuit_length_m": round(circuit_len, 1),
        "circuit_rotation": rotation_deg,
        "fps": FPS,
        "total_frames": len(frames),
        "duration_s": round(total_time, 2),
        "drivers": drivers_info,
        "status": "ready",
        "data_source": "fallback_demo",
        "notice": (
            "FastF1 cache/network telemetry was not found locally for this session; "
            "displaying deterministic 2025 simulation profile for interactive replay verification."
        ),
    }

    driver_meta_map = {d["code"]: d for d in drivers_info}
    lap_summaries = compute_lap_and_sector_summaries(frames, session=None, driver_colors=driver_colors)
    status_laps = compute_status_laps(frames, track_statuses)
    timeline_events = extract_timeline_events(frames, track_statuses, total_laps=total_laps)
    strategies = compute_strategy_summaries(
        frames=frames,
        lap_summaries=lap_summaries,
        session=None,
        driver_colors=driver_colors,
        total_laps=total_laps,
    )
    initial_leaderboard = build_leaderboard_snapshot(
        frames=frames,
        frame_index=0,
        track_statuses=track_statuses,
        driver_meta=driver_meta_map,
        lap_summaries=lap_summaries,
        total_laps=total_laps,
    )

    # Standings progression
    pts_table = [25, 18, 15, 12, 10, 8, 6, 4, 2, 1]
    live_driver_standings: Dict[str, Dict[str, float]] = {}
    live_constructor_standings: Dict[str, Dict[str, float]] = {}
    for lap_i in range(1, total_laps + 1):
        d_pts: Dict[str, float] = {}
        c_pts: Dict[str, float] = {}
        for idx_d, d_item in enumerate(drivers_info):
            p = float(pts_table[idx_d] if idx_d < len(pts_table) else 0.0)
            base_prior = max(0.0, (round_number - 1) * (p * 0.75))
            d_pts[d_item["code"]] = round(base_prior + p, 1)
            c_pts[d_item["team"]] = round(c_pts.get(d_item["team"], 0.0) + base_prior + p, 1)
        live_driver_standings[str(lap_i)] = dict(sorted(d_pts.items(), key=lambda x: x[1], reverse=True))
        live_constructor_standings[str(lap_i)] = dict(sorted(c_pts.items(), key=lambda x: x[1], reverse=True))

    return {
        "season": SUPPORTED_SEASON,
        "session": session_meta,
        "track_geometry": track_geometry,
        "driver_colors": driver_colors,
        "track_status": status_laps,
        "track_statuses": track_statuses,
        "race_control_messages": race_control_messages,
        "timeline_events": timeline_events,
        "lap_summaries": lap_summaries,
        "strategies": strategies,
        "leaderboard": [initial_leaderboard],
        "live_driver_standings": live_driver_standings,
        "live_constructor_standings": live_constructor_standings,
        "frames": frames,
    }
