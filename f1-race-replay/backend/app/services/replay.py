from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from src.lib.sectors import (
    SECTOR_KEYS,
    STATUS_NONE,
    best_sectors,
    classify_sector_statuses,
    session_best_holders,
    theoretical_best_s,
)
from src.lib.tyres import get_tyre_compound_int, get_tyre_compound_str
from src.tyre_degradation_integration import (
    TyreDegradationIntegrator,
    format_degradation_text,
)

STATUS_CODE_LABELS: Dict[str, str] = {
    "1": "GREEN",
    "2": "YELLOW",
    "3": "YELLOW",
    "4": "SC",
    "5": "RED",
    "6": "VSC",
    "7": "VSC ENDING",
}


def get_track_status_label(code: Any) -> str:
    raw = str(code or "1").strip()
    if raw in STATUS_CODE_LABELS:
        return STATUS_CODE_LABELS[raw]
    upper = raw.upper()
    if upper in ("GREEN", "YELLOW", "SC", "RED", "VSC"):
        return upper
    return "GREEN"


def rgb_tuple_to_hex(rgb: Any, default: str = "#FFFFFF") -> str:
    if isinstance(rgb, str) and rgb.startswith("#"):
        return rgb
    if isinstance(rgb, (tuple, list)) and len(rgb) >= 3:
        try:
            r, g, b = int(rgb[0]), int(rgb[1]), int(rgb[2])
            return f"#{max(0, min(255, r)):02X}{max(0, min(255, g)):02X}{max(0, min(255, b)):02X}"
        except (TypeError, ValueError):
            return default
    return default


def extract_drs_zones(
    x_val: np.ndarray, y_val: np.ndarray, drs_val: Optional[np.ndarray]
) -> List[Dict[str, Any]]:
    """
    Pure NumPy adaptation of plotDRSzones from src/ui_components.py.
    """
    if drs_val is None or len(drs_val) == 0:
        return []

    drs_zones: List[Dict[str, Any]] = []
    drs_start: Optional[int] = None

    for i, val in enumerate(drs_val):
        try:
            v_int = int(val)
        except (TypeError, ValueError):
            v_int = 0
        if v_int in (10, 12, 14):
            if drs_start is None:
                drs_start = i
        else:
            if drs_start is not None:
                drs_end = i - 1
                drs_zones.append(
                    {
                        "start": {
                            "x": round(float(x_val[drs_start]), 2),
                            "y": round(float(y_val[drs_start]), 2),
                            "index": int(drs_start),
                        },
                        "end": {
                            "x": round(float(x_val[drs_end]), 2),
                            "y": round(float(y_val[drs_end]), 2),
                            "index": int(drs_end),
                        },
                    }
                )
                drs_start = None

    if drs_start is not None:
        drs_end = len(drs_val) - 1
        drs_zones.append(
            {
                "start": {
                    "x": round(float(x_val[drs_start]), 2),
                    "y": round(float(y_val[drs_start]), 2),
                    "index": int(drs_start),
                },
                "end": {
                    "x": round(float(x_val[drs_end]), 2),
                    "y": round(float(y_val[drs_end]), 2),
                    "index": int(drs_end),
                },
            }
        )

    return drs_zones


def build_track_geometry_from_lap(
    example_lap: Any,
    rotation_deg: float = 0.0,
    track_width: float = 200.0,
    max_points: int = 500,
) -> Dict[str, Any]:
    """
    Arcade-free adaptation of build_track_from_example_lap from src/ui_components.py.
    Computes inner/outer track edges, world bounds, circuit length, and DRS zones.
    """
    if example_lap is None:
        return {
            "x_ref": [],
            "y_ref": [],
            "x_inner": [],
            "y_inner": [],
            "x_outer": [],
            "y_outer": [],
            "x_min": 0.0,
            "x_max": 1.0,
            "y_min": 0.0,
            "y_max": 1.0,
            "rotation_deg": float(rotation_deg or 0.0),
            "circuit_length_m": None,
            "drs_zones": [],
        }

    if isinstance(example_lap, pd.DataFrame):
        x_raw = example_lap["X"].to_numpy(dtype=float)
        y_raw = example_lap["Y"].to_numpy(dtype=float)
        drs_raw = (
            example_lap["DRS"].to_numpy(dtype=float)
            if "DRS" in example_lap.columns
            else None
        )
        circuit_length_m = (
            float(example_lap["Distance"].max())
            if "Distance" in example_lap.columns and len(example_lap["Distance"]) > 0
            else None
        )
    elif isinstance(example_lap, dict):
        x_raw = np.asarray(example_lap.get("X", []), dtype=float)
        y_raw = np.asarray(example_lap.get("Y", []), dtype=float)
        drs_raw = (
            np.asarray(example_lap.get("DRS", []), dtype=float)
            if "DRS" in example_lap
            else None
        )
        dist_arr = example_lap.get("Distance")
        circuit_length_m = (
            float(np.max(dist_arr))
            if dist_arr is not None and len(dist_arr) > 0
            else None
        )
    else:
        return {
            "x_ref": [],
            "y_ref": [],
            "x_inner": [],
            "y_inner": [],
            "x_outer": [],
            "y_outer": [],
            "x_min": 0.0,
            "x_max": 1.0,
            "y_min": 0.0,
            "y_max": 1.0,
            "rotation_deg": float(rotation_deg or 0.0),
            "circuit_length_m": None,
            "drs_zones": [],
        }

    if len(x_raw) < 3:
        return {
            "x_ref": [],
            "y_ref": [],
            "x_inner": [],
            "y_inner": [],
            "x_outer": [],
            "y_outer": [],
            "x_min": 0.0,
            "x_max": 1.0,
            "y_min": 0.0,
            "y_max": 1.0,
            "rotation_deg": float(rotation_deg or 0.0),
            "circuit_length_m": circuit_length_m,
            "drs_zones": [],
        }

    # Downsample if very dense while preserving indices
    if len(x_raw) > max_points:
        idxs = np.linspace(0, len(x_raw) - 1, max_points, dtype=int)
        x_ref = x_raw[idxs]
        y_ref = y_raw[idxs]
        drs_ref = drs_raw[idxs] if drs_raw is not None and len(drs_raw) == len(x_raw) else None
    else:
        x_ref = x_raw
        y_ref = y_raw
        drs_ref = drs_raw

    dx = np.gradient(x_ref)
    dy = np.gradient(y_ref)
    norm = np.sqrt(dx**2 + dy**2)
    norm[norm == 0] = 1.0
    dx = dx / norm
    dy = dy / norm

    nx = -dy
    ny = dx

    x_outer = x_ref + nx * (track_width / 2.0)
    y_outer = y_ref + ny * (track_width / 2.0)
    x_inner = x_ref - nx * (track_width / 2.0)
    y_inner = y_ref - ny * (track_width / 2.0)

    x_min = float(min(x_ref.min(), x_inner.min(), x_outer.min()))
    x_max = float(max(x_ref.max(), x_inner.max(), x_outer.max()))
    y_min = float(min(y_ref.min(), y_inner.min(), y_outer.min()))
    y_max = float(max(y_ref.max(), y_inner.max(), y_outer.max()))

    if circuit_length_m is None:
        seg_lengths = np.sqrt(np.diff(x_ref) ** 2 + np.diff(y_ref) ** 2)
        circuit_length_m = round(float(np.sum(seg_lengths)) / 10.0, 1)

    drs_zones = extract_drs_zones(x_outer, y_outer, drs_ref)

    return {
        "x_ref": [round(float(v), 2) for v in x_ref],
        "y_ref": [round(float(v), 2) for v in y_ref],
        "x_inner": [round(float(v), 2) for v in x_inner],
        "y_inner": [round(float(v), 2) for v in y_inner],
        "x_outer": [round(float(v), 2) for v in x_outer],
        "y_outer": [round(float(v), 2) for v in y_outer],
        "x_min": round(x_min, 2),
        "x_max": round(x_max, 2),
        "y_min": round(y_min, 2),
        "y_max": round(y_max, 2),
        "rotation_deg": float(rotation_deg or 0.0),
        "circuit_length_m": round(float(circuit_length_m), 2) if circuit_length_m else None,
        "drs_zones": drs_zones,
    }


def extract_timeline_events(
    frames: List[Dict[str, Any]],
    track_statuses: List[Dict[str, Any]],
    total_laps: int = 0,
    fps: int = 25,
) -> List[Dict[str, Any]]:
    """
    Arcade-free adaptation of extract_race_events from src/ui_components.py.
    """
    events: List[Dict[str, Any]] = []
    if not frames:
        return events

    n_frames = len(frames)
    prev_drivers: set[str] = set()
    sample_rate = max(1, fps)

    for i in range(0, n_frames, sample_rate):
        frame = frames[i]
        drivers_data = frame.get("drivers", {})
        current_drivers = set(drivers_data.keys())

        if prev_drivers:
            dnf_drivers = prev_drivers - current_drivers
            for driver_code in sorted(dnf_drivers):
                prev_frame = frames[max(0, i - sample_rate)]
                driver_info = prev_frame.get("drivers", {}).get(driver_code, {})
                lap = driver_info.get("lap", 1)
                events.append(
                    {
                        "type": "dnf",
                        "frame": int(i),
                        "end_frame": None,
                        "label": f"{driver_code} OUT",
                        "lap": int(lap) if isinstance(lap, (int, float)) else None,
                    }
                )
        prev_drivers = current_drivers

    for status in track_statuses or []:
        status_code = str(status.get("status", ""))
        start_time = float(status.get("start_time", 0.0))
        end_time = status.get("end_time")

        start_frame = max(0, int(start_time * fps))
        end_frame = int(float(end_time) * fps) if end_time is not None else start_frame + 10 * fps

        if end_frame <= 0:
            continue
        if n_frames > 0:
            end_frame = min(end_frame, n_frames - 1)

        event_type = None
        label = ""
        if status_code == "2":
            event_type = "yellow_flag"
            label = "Yellow Flag"
        elif status_code == "4":
            event_type = "safety_car"
            label = "Safety Car"
        elif status_code == "5":
            event_type = "red_flag"
            label = "Red Flag"
        elif status_code in ("6", "7"):
            event_type = "vsc"
            label = "VSC"

        if event_type:
            events.append(
                {
                    "type": event_type,
                    "frame": start_frame,
                    "end_frame": end_frame,
                    "label": label,
                    "lap": None,
                }
            )

    return events


def compute_status_laps(
    frames: List[Dict[str, Any]], track_statuses: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Arcade-free adaptation of F1RaceReplayWindow._compute_status_laps from src/interfaces/race_replay.py.
    """
    if not track_statuses or not frames:
        return []

    time_to_lap: List[Tuple[float, int]] = []
    step = max(1, min(25, len(frames) // 20 or 1))
    for i in range(0, len(frames), step):
        f = frames[i]
        t = float(f.get("t", 0.0))
        lap = int(f.get("lap", 1))
        time_to_lap.append((t, lap))

    def _lap_at_time(target_t: float) -> int:
        best_lap = 1
        for t, lap in time_to_lap:
            if t <= target_t:
                best_lap = lap
            else:
                break
        return best_lap

    result: List[Dict[str, Any]] = []
    for status in track_statuses:
        code = str(status.get("status", ""))
        if code not in ("2", "4", "5", "6", "7"):
            continue
        start_t = float(status.get("start_time", 0.0))
        end_t = status.get("end_time")
        start_lap = _lap_at_time(start_t)
        end_lap = _lap_at_time(float(end_t)) if end_t is not None else start_lap
        if (
            result
            and result[-1]["status"] == code
            and result[-1]["end_lap"] >= start_lap - 1
        ):
            result[-1]["end_lap"] = max(result[-1]["end_lap"], end_lap)
        else:
            result.append(
                {
                    "status": code,
                    "label": get_track_status_label(code),
                    "start_time": round(start_t, 3),
                    "end_time": round(float(end_t), 3) if end_t is not None else None,
                    "start_lap": start_lap,
                    "end_lap": end_lap,
                }
            )
    return result


def compute_fallback_lap_times(
    frames: List[Dict[str, Any]],
    min_lap_time_s: float = 20.0,
    max_lap_time_s: float = 7200.0,
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Derive per-driver lap times from replay frames when official FastF1 lap records
    are missing or incomplete.
    """
    lap_start_t: Dict[str, float] = {}
    current_lap: Dict[str, int] = {}
    result: Dict[str, List[Dict[str, Any]]] = {}

    for frame in frames:
        t = float(frame.get("t", 0.0))
        drivers = frame.get("drivers", {})
        for code, drv in drivers.items():
            lap_val = drv.get("lap")
            if lap_val is None:
                continue
            lap = int(round(float(lap_val)))
            prev_lap = current_lap.get(code)
            if prev_lap is None:
                current_lap[code] = lap
                lap_start_t[code] = t
                result.setdefault(code, [])
                continue

            if lap > prev_lap:
                lap_time = t - lap_start_t.get(code, t)
                tyre = int(round(float(drv.get("tyre", -1))))
                tyre_life = int(round(float(drv.get("tyre_life", 0))))
                in_pit = bool(drv.get("in_pit", False))

                if min_lap_time_s < lap_time < max_lap_time_s and prev_lap >= 1:
                    s1 = round(lap_time * 0.31, 3)
                    s2 = round(lap_time * 0.38, 3)
                    s3 = round(lap_time - s1 - s2, 3)
                    result.setdefault(code, []).append(
                        {
                            "lap": int(prev_lap),
                            "time_s": round(float(lap_time), 3),
                            "end_time_s": round(float(t), 3),
                            "start_time_s": round(float(lap_start_t.get(code, t)), 3),
                            "sector1_s": s1,
                            "sector2_s": s2,
                            "sector3_s": s3,
                            "tyre": tyre,
                            "tyre_life": tyre_life,
                            "is_pit_entry": in_pit,
                            "is_pit_affected": in_pit,
                            "is_out_lap": False,
                            "is_outlier": False,
                            "source": "derived",
                        }
                    )
                current_lap[code] = lap
                lap_start_t[code] = t

    return result


def compute_lap_and_sector_summaries(
    frames: List[Dict[str, Any]],
    session: Any = None,
    driver_colors: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Build per-driver lap & sector summaries with official F1 purple/green sector
    classifications (using src/lib/sectors.py) and 3-lap rolling averages.
    """
    driver_colors = driver_colors or {}
    raw_by_code: Dict[str, List[Dict[str, Any]]] = {}
    fallback_by_code = compute_fallback_lap_times(frames)

    if session is not None and hasattr(session, "laps") and session.laps is not None:
        try:
            laps_df = session.laps
            if not laps_df.empty:
                for _, row in laps_df.iterrows():
                    code = str(row.get("Driver", "")).strip()
                    lap_num = row.get("LapNumber")
                    if not code or pd.isna(lap_num):
                        continue
                    lap_int = int(lap_num)
                    lap_time_td = row.get("LapTime")
                    time_s = (
                        round(float(lap_time_td.total_seconds()), 3)
                        if pd.notna(lap_time_td)
                        else None
                    )
                    end_td = row.get("Time")
                    end_time_s = (
                        round(float(end_td.total_seconds()), 3)
                        if pd.notna(end_td)
                        else None
                    )
                    tyre_str = row.get("Compound")
                    tyre_int = (
                        get_tyre_compound_int(str(tyre_str))
                        if pd.notna(tyre_str)
                        else -1
                    )
                    tyre_life_val = row.get("TyreLife")
                    tyre_life = (
                        int(tyre_life_val) if pd.notna(tyre_life_val) else 0
                    )
                    is_pit_in = (
                        "PitInTime" in laps_df.columns
                        and pd.notna(row.get("PitInTime"))
                    )
                    is_pit_out = (
                        "PitOutTime" in laps_df.columns
                        and pd.notna(row.get("PitOutTime"))
                    )

                    def _sec(col_name: str) -> Optional[float]:
                        val = row.get(col_name)
                        return (
                            round(float(val.total_seconds()), 3)
                            if pd.notna(val) and hasattr(val, "total_seconds")
                            else None
                        )

                    raw_by_code.setdefault(code, []).append(
                        {
                            "lap": lap_int,
                            "time_s": time_s if (time_s and time_s > 0) else None,
                            "end_time_s": end_time_s,
                            "sector1_s": _sec("Sector1Time"),
                            "sector2_s": _sec("Sector2Time"),
                            "sector3_s": _sec("Sector3Time"),
                            "tyre": tyre_int,
                            "tyre_life": tyre_life,
                            "is_pit_entry": bool(is_pit_in),
                            "is_pit_affected": bool(is_pit_in or is_pit_out),
                            "is_out_lap": bool(is_pit_out),
                            "is_outlier": False,
                            "source": "official",
                        }
                    )
        except Exception as exc:
            print(f"Warning: could not parse official session.laps, using fallback: {exc}")

    if not raw_by_code:
        raw_by_code = fallback_by_code
    else:
        # Backfill missing times from frame-derived fallback
        for code, entries in raw_by_code.items():
            fb_map = {e["lap"]: e for e in fallback_by_code.get(code, [])}
            for entry in entries:
                fb = fb_map.get(entry["lap"])
                if fb and (entry.get("time_s") is None or entry["time_s"] <= 0):
                    entry["time_s"] = fb.get("time_s")
                    entry["source"] = "derived"

    # Sort laps per driver and compute sector statuses using src/lib/sectors.py
    for entries in raw_by_code.values():
        entries.sort(key=lambda e: e["lap"])

    sector_statuses = classify_sector_statuses(raw_by_code)
    best_holders = session_best_holders(raw_by_code)

    # Calculate per-lap leader times for gap-to-leader on lap chart
    leader_lap_clock: Dict[int, float] = {}
    driver_cum_time: Dict[str, Dict[int, float]] = {}
    for code, entries in raw_by_code.items():
        cum = 0.0
        driver_cum_time[code] = {}
        for e in entries:
            t_s = e.get("time_s")
            if isinstance(t_s, (int, float)) and t_s > 0:
                cum += float(t_s)
                lap_n = int(e["lap"])
                driver_cum_time[code][lap_n] = cum
                if lap_n not in leader_lap_clock or cum < leader_lap_clock[lap_n]:
                    leader_lap_clock[lap_n] = cum

    drivers_summary: Dict[str, Dict[str, Any]] = {}
    for code, entries in raw_by_code.items():
        clean_window: List[float] = []
        formatted_laps: List[Dict[str, Any]] = []
        valid_lap_times: List[float] = []

        for entry in entries:
            lap_n = int(entry["lap"])
            t_s = entry.get("time_s")
            if isinstance(t_s, (int, float)) and t_s > 0:
                valid_lap_times.append(float(t_s))
                if not entry.get("is_pit_affected") and not entry.get("is_out_lap"):
                    clean_window.append(float(t_s))

            ma_3 = (
                round(sum(clean_window[-3:]) / len(clean_window[-3:]), 3)
                if len(clean_window) >= 1 and isinstance(t_s, (int, float)) and t_s > 0
                else None
            )

            st = sector_statuses.get((code, lap_n), {})
            tyre_int = int(entry.get("tyre", -1))
            cum_t = driver_cum_time.get(code, {}).get(lap_n)
            leader_t = leader_lap_clock.get(lap_n)
            gap_s = (
                round(cum_t - leader_t, 3)
                if cum_t is not None and leader_t is not None
                else None
            )

            formatted_laps.append(
                {
                    "lap": lap_n,
                    "time_s": t_s,
                    "sector1_s": entry.get("sector1_s"),
                    "sector2_s": entry.get("sector2_s"),
                    "sector3_s": entry.get("sector3_s"),
                    "sector1_status": st.get("sector1_s", STATUS_NONE),
                    "sector2_status": st.get("sector2_s", STATUS_NONE),
                    "sector3_status": st.get("sector3_s", STATUS_NONE),
                    "tyre": tyre_int,
                    "tyre_compound": get_tyre_compound_str(tyre_int),
                    "tyre_life": int(entry.get("tyre_life", 0)),
                    "is_pit_entry": bool(entry.get("is_pit_entry", False)),
                    "is_out_lap": bool(entry.get("is_out_lap", False)),
                    "is_pit_affected": bool(entry.get("is_pit_affected", False)),
                    "is_outlier": bool(entry.get("is_outlier", False)),
                    "end_time_s": entry.get("end_time_s"),
                    "official_gap_to_leader_s": gap_s,
                    "moving_avg_3_s": ma_3,
                    "source": entry.get("source", "official"),
                }
            )

        bests = best_sectors(entries)
        theo_best = theoretical_best_s(entries)
        drivers_summary[code] = {
            "code": code,
            "color": rgb_tuple_to_hex(driver_colors.get(code), "#FFFFFF"),
            "best_lap_s": round(min(valid_lap_times), 3) if valid_lap_times else None,
            "theoretical_best_s": round(float(theo_best), 3) if theo_best is not None else None,
            "best_sectors": {
                k: round(float(v), 3) if v is not None else None
                for k, v in bests.items()
            },
            "laps": formatted_laps,
        }

    session_bests_formatted = {
        k: {
            "time_s": round(float(val[0]), 3) if val[0] is not None else None,
            "holders": val[1],
        }
        for k, val in best_holders.items()
    }

    return {
        "drivers": drivers_summary,
        "session_best_sectors": session_bests_formatted,
    }


def compute_strategy_summaries(
    frames: List[Dict[str, Any]],
    lap_summaries: Dict[str, Any],
    session: Any = None,
    driver_colors: Optional[Dict[str, Any]] = None,
    total_laps: int = 0,
) -> List[Dict[str, Any]]:
    """
    Build tyre strategy stints per driver and integrate Bayesian tyre degradation
    health metrics using TyreDegradationIntegrator (src/tyre_degradation_integration.py).
    """
    driver_colors = driver_colors or {}
    degradation_integrator: Optional[TyreDegradationIntegrator] = None

    if session is not None and hasattr(session, "laps") and session.laps is not None:
        try:
            integrator = TyreDegradationIntegrator(session=session)
            if integrator.initialize_from_session():
                degradation_integrator = integrator
        except Exception as exc:
            print(f"Note: Bayesian tyre degradation fallback active: {exc}")

    final_positions: Dict[str, int] = {}
    if frames:
        last_drivers = frames[-1].get("drivers", {})
        for code, dstate in last_drivers.items():
            pos = dstate.get("position")
            if isinstance(pos, (int, float)):
                final_positions[code] = int(pos)

    drivers_laps = lap_summaries.get("drivers", {})
    all_codes = sorted(
        set(drivers_laps.keys()) | set(final_positions.keys()),
        key=lambda c: final_positions.get(c, 99),
    )

    strategies: List[Dict[str, Any]] = []
    for code in all_codes:
        lap_entries = drivers_laps.get(code, {}).get("laps", [])
        stints: List[Dict[str, Any]] = []

        if lap_entries:
            current_stint: Optional[Dict[str, Any]] = None
            for entry in lap_entries:
                lap_n = int(entry.get("lap", 1))
                tyre_int = int(entry.get("tyre", -1))
                compound_name = get_tyre_compound_str(tyre_int)
                tyre_life = int(entry.get("tyre_life", 1))
                is_out = bool(entry.get("is_out_lap", False))

                if (
                    current_stint is None
                    or current_stint["compound_int"] != tyre_int
                    or is_out
                ):
                    if current_stint is not None:
                        stints.append(current_stint)
                    current_stint = {
                        "stint_number": len(stints) + 1,
                        "compound": compound_name,
                        "compound_int": tyre_int,
                        "start_lap": lap_n,
                        "end_lap": lap_n,
                        "lap_count": 1,
                        "max_tyre_life": max(1, tyre_life),
                    }
                else:
                    current_stint["end_lap"] = lap_n
                    current_stint["lap_count"] = (
                        current_stint["end_lap"] - current_stint["start_lap"] + 1
                    )
                    current_stint["max_tyre_life"] = max(
                        current_stint["max_tyre_life"], tyre_life, current_stint["lap_count"]
                    )
            if current_stint is not None:
                stints.append(current_stint)
        elif frames:
            # Derive stints directly from sampled frames
            current_stint = None
            step = max(1, len(frames) // 100)
            for idx in range(0, len(frames), step):
                d = frames[idx].get("drivers", {}).get(code)
                if not d:
                    continue
                lap_n = max(1, int(round(float(d.get("lap", 1)))))
                tyre_int = int(round(float(d.get("tyre", -1))))
                compound_name = get_tyre_compound_str(tyre_int)
                tyre_life = max(1, int(round(float(d.get("tyre_life", 1)))))
                if current_stint is None or current_stint["compound_int"] != tyre_int:
                    if current_stint is not None:
                        stints.append(current_stint)
                    current_stint = {
                        "stint_number": len(stints) + 1,
                        "compound": compound_name,
                        "compound_int": tyre_int,
                        "start_lap": lap_n,
                        "end_lap": lap_n,
                        "lap_count": 1,
                        "max_tyre_life": tyre_life,
                    }
                else:
                    current_stint["end_lap"] = max(current_stint["end_lap"], lap_n)
                    current_stint["lap_count"] = (
                        current_stint["end_lap"] - current_stint["start_lap"] + 1
                    )
                    current_stint["max_tyre_life"] = max(
                        current_stint["max_tyre_life"], tyre_life
                    )
            if current_stint is not None:
                stints.append(current_stint)

        last_stint = stints[-1] if stints else None
        last_lap = last_stint["end_lap"] if last_stint else (total_laps or 1)
        deg_info: Optional[Dict[str, Any]] = None

        if degradation_integrator is not None:
            raw_health = degradation_integrator.get_tyre_health(code, last_lap, "DRY")
            if raw_health:
                deg_info = {
                    "driver_code": code,
                    "compound": str(raw_health.get("compound", "UNKNOWN")),
                    "laps_on_tyre": int(raw_health.get("laps_on_tyre", 0)),
                    "health_pct": round(float(raw_health.get("health", 100.0)), 1),
                    "expected_delta_s": round(
                        float(raw_health.get("expected_delta", 0.0)), 3
                    ),
                    "degradation_rate_s_per_lap": round(
                        float(raw_health.get("degradation_rate", 0.03)), 4
                    ),
                    "overdriving": bool(raw_health.get("overdriving", False)),
                    "uncertainty_s": round(
                        float(raw_health.get("uncertainty", 0.1)), 3
                    ),
                    "summary_text": format_degradation_text(raw_health),
                }

        if deg_info is None and last_stint is not None:
            # Deterministic Bayesian-prior fallback based on TyreProfile priors in src/bayesian_tyre_model.py
            priors = {
                "SOFT": (0.05, 2.0),
                "MEDIUM": (0.03, 2.0),
                "HARD": (0.01, 2.0),
                "INTERMEDIATE": (0.04, 3.0),
                "WET": (0.02, 2.5),
            }
            comp = last_stint["compound"]
            rate, max_deg = priors.get(comp, (0.03, 2.0))
            laps_on = int(last_stint["max_tyre_life"])
            expected_delta = min(max_deg, laps_on * rate)
            health_pct = max(0.0, min(100.0, round(100.0 * (1.0 - expected_delta / max_deg), 1)))
            synthetic_raw = {
                "compound": comp,
                "laps_on_tyre": laps_on,
                "health": int(round(health_pct)),
                "expected_delta": expected_delta,
                "overdriving": False,
                "uncertainty": 0.12,
            }
            deg_info = {
                "driver_code": code,
                "compound": comp,
                "laps_on_tyre": laps_on,
                "health_pct": health_pct,
                "expected_delta_s": round(expected_delta, 3),
                "degradation_rate_s_per_lap": rate,
                "overdriving": False,
                "uncertainty_s": 0.12,
                "summary_text": format_degradation_text(synthetic_raw),
            }

        strategies.append(
            {
                "code": code,
                "position": final_positions.get(code),
                "color": rgb_tuple_to_hex(driver_colors.get(code), "#FFFFFF"),
                "pit_stops": max(0, len(stints) - 1),
                "pit_windows_s": [],
                "stints": stints,
                "degradation": deg_info,
            }
        )

    return strategies


def build_leaderboard_snapshot(
    frames: List[Dict[str, Any]],
    frame_index: int,
    track_statuses: List[Dict[str, Any]],
    driver_meta: Dict[str, Dict[str, Any]],
    lap_summaries: Optional[Dict[str, Any]] = None,
    total_laps: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Build a serializable LeaderboardSnapshot for a given frame_index, preserving
    the exact gap-to-leader and interval calculation from LeaderboardComponent._calculate_gaps
    in src/ui_components.py.
    """
    if not frames:
        return {
            "frame_index": 0,
            "time_s": 0.0,
            "lap": 1,
            "total_laps": total_laps,
            "track_status": "1",
            "track_status_label": "GREEN",
            "entries": [],
        }

    clamped_idx = max(0, min(int(frame_index), len(frames) - 1))
    frame = frames[clamped_idx]
    t = float(frame.get("t", 0.0))
    lap = int(frame.get("lap", 1))

    active_status = "1"
    for st in track_statuses or []:
        s_t = float(st.get("start_time", 0.0))
        e_t = st.get("end_time")
        if t >= s_t and (e_t is None or t < float(e_t)):
            active_status = str(st.get("status", "1"))
            break

    drivers_dict = frame.get("drivers", {})
    sorted_drivers = sorted(
        drivers_dict.items(),
        key=lambda kv: (
            kv[1].get("position", 999),
            -float(kv[1].get("lap", 0)),
            -float(kv[1].get("dist", 0.0)),
        ),
    )

    leader_dist = (
        float(sorted_drivers[0][1].get("dist", 0.0)) if sorted_drivers else 0.0
    )
    entries: List[Dict[str, Any]] = []
    lap_drivers = (lap_summaries or {}).get("drivers", {})

    for idx, (code, d) in enumerate(sorted_drivers):
        pos = idx + 1
        dist_val = float(d.get("dist", 0.0))
        raw_to_leader = max(0.0, leader_dist - dist_val)
        gap_to_leader_s = 0.0 if idx == 0 else round((raw_to_leader / 10.0) / 55.56, 2)

        if idx == 0:
            interval_s = 0.0
        else:
            prev_dist = float(sorted_drivers[idx - 1][1].get("dist", 0.0))
            raw_ahead = max(0.0, prev_dist - dist_val)
            interval_s = round((raw_ahead / 10.0) / 55.56, 2)

        tyre_int = int(round(float(d.get("tyre", -1))))
        meta = driver_meta.get(code, {})
        drv_laps = lap_drivers.get(code, {}).get("laps", [])
        completed_laps = [
            l["time_s"]
            for l in drv_laps
            if l.get("lap", 0) < int(d.get("lap", 1)) and isinstance(l.get("time_s"), (int, float))
        ]
        last_lap_s = completed_laps[-1] if completed_laps else None
        best_lap_s = min(completed_laps) if completed_laps else lap_drivers.get(code, {}).get("best_lap_s")

        entries.append(
            {
                "position": pos,
                "code": code,
                "full_name": meta.get("full_name", code),
                "team": meta.get("team"),
                "color": meta.get("color", "#FFFFFF"),
                "lap": int(round(float(d.get("lap", 1)))),
                "tyre": tyre_int,
                "tyre_compound": get_tyre_compound_str(tyre_int),
                "tyre_life": int(round(float(d.get("tyre_life", 0)))),
                "in_pit": bool(d.get("in_pit", False)),
                "is_out": bool(float(d.get("rel_dist", 0.0)) >= 0.9999 and pos > 15 and float(d.get("speed", 0.0)) < 1.0),
                "speed_kph": round(float(d.get("speed", 0.0)), 1),
                "gear": int(d.get("gear", 0)),
                "drs_active": int(d.get("drs", 0)) in (10, 12, 14),
                "gap_to_leader_s": gap_to_leader_s,
                "interval_s": interval_s,
                "last_lap_s": last_lap_s,
                "best_lap_s": best_lap_s,
            }
        )

    return {
        "frame_index": clamped_idx,
        "time_s": round(t, 3),
        "lap": lap,
        "total_laps": total_laps,
        "track_status": active_status,
        "track_status_label": get_track_status_label(active_status),
        "entries": entries,
    }
