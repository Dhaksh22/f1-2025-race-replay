from __future__ import annotations

from typing import Any, Dict, List, Optional

from backend.app.services.replay import rgb_tuple_to_hex
from src.lib.tyres import get_tyre_compound_str


def extract_driver_telemetry_series(
    payload: Dict[str, Any],
    driver_code: str,
    mode: str = "lap",
    lap: Optional[int] = None,
    start_time: Optional[float] = None,
    end_time: Optional[float] = None,
    segment: Optional[str] = None,
    max_samples: int = 350,
) -> Dict[str, Any]:
    """
    Extract telemetry samples (speed, throttle, brake, gear, DRS) for a driver
    from a loaded replay payload (race, qualifying, or practice).
    Preserves the brake 0-100% scaling and lap-relative distance from
    src/insights/driver_telemetry_window.py and src/f1_data.py.
    """
    code = str(driver_code or "").upper().strip()
    driver_colors = payload.get("driver_colors", {})
    color_hex = rgb_tuple_to_hex(driver_colors.get(code), "#FFFFFF")
    session_meta = payload.get("session", {})
    session_type = str(session_meta.get("session_type", "R")).upper()

    # Handle Qualifying / Practice telemetry structure if present
    quali_or_practice = payload.get("quali_practice_telemetry", {})
    if session_type in ("Q", "SQ") and code in quali_or_practice:
        drv_qp = quali_or_practice[code]
        seg = (segment or "Q3").upper()
        if seg not in ("Q1", "Q2", "Q3") or not drv_qp.get(seg, {}).get("frames"):
            for candidate in ("Q3", "Q2", "Q1"):
                if drv_qp.get(candidate, {}).get("frames"):
                    seg = candidate
                    break
        seg_data = drv_qp.get(seg, {})
        raw_frames = seg_data.get("frames", [])
        samples = _frames_to_telemetry_samples(raw_frames, max_samples=max_samples, is_quali=True)
        speeds = [s["speed_kph"] for s in samples]
        sec_times = seg_data.get("sector_times", {})
        comp_int = seg_data.get("compound", -1)
        return {
            "code": code,
            "color": color_hex,
            "mode": "quali_segment",
            "lap": 1,
            "segment": seg,
            "lap_time_s": samples[-1]["t"] if samples else None,
            "sector1_s": sec_times.get("sector1"),
            "sector2_s": sec_times.get("sector2"),
            "sector3_s": sec_times.get("sector3"),
            "compound": get_tyre_compound_str(int(comp_int)) if isinstance(comp_int, (int, float)) else "SOFT",
            "max_speed_kph": round(max(speeds), 1) if speeds else None,
            "min_speed_kph": round(min(speeds), 1) if speeds else None,
            "samples": samples,
        }

    if session_type in ("FP1", "FP2", "FP3") and code in quali_or_practice:
        best_lap = quali_or_practice[code].get("best_lap", {})
        raw_frames = best_lap.get("frames", [])
        samples = _frames_to_telemetry_samples(raw_frames, max_samples=max_samples, is_quali=True)
        speeds = [s["speed_kph"] for s in samples]
        sec_times = best_lap.get("sector_times", {})
        return {
            "code": code,
            "color": color_hex,
            "mode": "best_lap",
            "lap": 1,
            "segment": session_type,
            "lap_time_s": samples[-1]["t"] if samples else None,
            "sector1_s": sec_times.get("sector1"),
            "sector2_s": sec_times.get("sector2"),
            "sector3_s": sec_times.get("sector3"),
            "compound": "MEDIUM",
            "max_speed_kph": round(max(speeds), 1) if speeds else None,
            "min_speed_kph": round(min(speeds), 1) if speeds else None,
            "samples": samples,
        }

    # Standard Race / Sprint frame extraction
    frames: List[Dict[str, Any]] = payload.get("frames", [])
    if not frames:
        return {
            "code": code,
            "color": color_hex,
            "mode": "time" if mode == "time" else "lap",
            "lap": lap,
            "segment": None,
            "lap_time_s": None,
            "sector1_s": None,
            "sector2_s": None,
            "sector3_s": None,
            "compound": None,
            "max_speed_kph": None,
            "min_speed_kph": None,
            "samples": [],
        }

    matched: List[Dict[str, Any]] = []
    if mode == "time":
        t_end = float(end_time) if end_time is not None else float(frames[-1].get("t", 0.0))
        t_start = float(start_time) if start_time is not None else max(0.0, t_end - 30.0)
        for f in frames:
            t_val = float(f.get("t", 0.0))
            if t_start <= t_val <= t_end:
                d = f.get("drivers", {}).get(code)
                if d is not None:
                    matched.append((t_val, d))
    else:
        # Lap mode: find target lap (defaults to median/first available lap if not specified)
        available_laps = sorted(
            {
                int(round(float(f["drivers"][code].get("lap", 1))))
                for f in frames
                if code in f.get("drivers", {})
            }
        )
        target_lap = int(lap) if (lap is not None and int(lap) in available_laps) else (available_laps[len(available_laps) // 2] if available_laps else 1)
        lap = target_lap
        for f in frames:
            d = f.get("drivers", {}).get(code)
            if d is not None and int(round(float(d.get("lap", 1)))) == target_lap:
                matched.append((float(f.get("t", 0.0)), d))

    if not matched:
        return {
            "code": code,
            "color": color_hex,
            "mode": "time" if mode == "time" else "lap",
            "lap": lap,
            "segment": None,
            "lap_time_s": None,
            "sector1_s": None,
            "sector2_s": None,
            "sector3_s": None,
            "compound": None,
            "max_speed_kph": None,
            "min_speed_kph": None,
            "samples": [],
        }

    # Downsample if needed
    if len(matched) > max_samples:
        step = max(1, len(matched) // max_samples)
        sampled = matched[::step]
        if sampled[-1] != matched[-1]:
            sampled.append(matched[-1])
    else:
        sampled = matched

    start_dist = float(sampled[0][1].get("dist", 0.0))
    t0 = float(sampled[0][0])

    samples: List[Dict[str, Any]] = []
    for t_val, d in sampled:
        raw_brake = float(d.get("brake", 0.0) or 0.0)
        brake_pct = raw_brake * 100.0 if raw_brake <= 1.05 else raw_brake
        dist_val = float(d.get("dist", 0.0) or 0.0)
        lap_dist = max(0.0, dist_val - start_dist) if mode != "time" else dist_val
        samples.append(
            {
                "t": round(t_val if mode == "time" else (t_val - t0), 3),
                "dist_m": round(lap_dist, 1),
                "rel_dist": round(float(d.get("rel_dist", 0.0) or 0.0), 4),
                "lap": int(round(float(d.get("lap", 1)))),
                "speed_kph": round(float(d.get("speed", 0.0) or 0.0), 1),
                "throttle_pct": round(float(d.get("throttle", 0.0) or 0.0), 1),
                "brake_pct": round(min(100.0, max(0.0, brake_pct)), 1),
                "gear": int(d.get("gear", 0) or 0),
                "drs": int(d.get("drs", 0) or 0),
            }
        )

    speeds = [s["speed_kph"] for s in samples]
    tyre_int = int(round(float(sampled[0][1].get("tyre", -1))))
    compound_str = get_tyre_compound_str(tyre_int)

    # Enrich with official lap/sector times if available in lap_summaries
    lap_time_s = round(matched[-1][0] - matched[0][0], 3) if len(matched) > 1 else None
    s1_s, s2_s, s3_s = None, None, None
    lap_drivers = payload.get("lap_summaries", {}).get("drivers", {})
    if code in lap_drivers and lap is not None:
        for l_entry in lap_drivers[code].get("laps", []):
            if l_entry.get("lap") == lap:
                lap_time_s = l_entry.get("time_s") or lap_time_s
                s1_s = l_entry.get("sector1_s")
                s2_s = l_entry.get("sector2_s")
                s3_s = l_entry.get("sector3_s")
                break

    return {
        "code": code,
        "color": color_hex,
        "mode": "time" if mode == "time" else "lap",
        "lap": lap,
        "segment": None,
        "lap_time_s": lap_time_s,
        "sector1_s": s1_s,
        "sector2_s": s2_s,
        "sector3_s": s3_s,
        "compound": compound_str,
        "max_speed_kph": round(max(speeds), 1) if speeds else None,
        "min_speed_kph": round(min(speeds), 1) if speeds else None,
        "samples": samples,
    }


def _frames_to_telemetry_samples(
    raw_frames: List[Dict[str, Any]], max_samples: int = 350, is_quali: bool = True
) -> List[Dict[str, Any]]:
    if not raw_frames:
        return []
    if len(raw_frames) > max_samples:
        step = max(1, len(raw_frames) // max_samples)
        sliced = raw_frames[::step]
        if sliced[-1] != raw_frames[-1]:
            sliced.append(raw_frames[-1])
    else:
        sliced = raw_frames

    t0 = float(sliced[0].get("t", 0.0)) if sliced else 0.0
    out: List[Dict[str, Any]] = []
    for f in sliced:
        tel = f.get("telemetry", f)
        raw_brake = float(tel.get("brake", 0.0) or 0.0)
        brake_pct = raw_brake * 100.0 if raw_brake <= 1.05 else raw_brake
        out.append(
            {
                "t": round(float(f.get("t", 0.0)) - (0.0 if is_quali else t0), 3),
                "dist_m": round(float(tel.get("dist", 0.0) or 0.0), 1),
                "rel_dist": round(float(tel.get("rel_dist", 0.0) or 0.0), 4),
                "lap": 1,
                "speed_kph": round(float(tel.get("speed", 0.0) or 0.0), 1),
                "throttle_pct": round(float(tel.get("throttle", 0.0) or 0.0), 1),
                "brake_pct": round(min(100.0, max(0.0, brake_pct)), 1),
                "gear": int(tel.get("gear", 0) or 0),
                "drs": int(tel.get("drs", 0) or 0),
            }
        )
    return out


def compare_driver_telemetry(
    payload: Dict[str, Any],
    primary_driver: str,
    compare_driver: Optional[str] = None,
    mode: str = "lap",
    lap: Optional[int] = None,
    start_time: Optional[float] = None,
    end_time: Optional[float] = None,
    segment: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Extract telemetry for primary_driver and optional compare_driver, plus compute
    comparative metrics (top speed delta, average speed delta, full throttle %, braking %).
    """
    primary = extract_driver_telemetry_series(
        payload=payload,
        driver_code=primary_driver,
        mode=mode,
        lap=lap,
        start_time=start_time,
        end_time=end_time,
        segment=segment,
    )
    comparison = None
    delta_summary = None

    if compare_driver and compare_driver.strip().upper() != primary["code"]:
        comparison = extract_driver_telemetry_series(
            payload=payload,
            driver_code=compare_driver,
            mode=mode,
            lap=primary.get("lap") if mode == "lap" else lap,
            start_time=start_time,
            end_time=end_time,
            segment=segment,
        )
        p_samples = primary.get("samples", [])
        c_samples = comparison.get("samples", [])
        if p_samples and c_samples:
            p_avg_speed = sum(s["speed_kph"] for s in p_samples) / len(p_samples)
            c_avg_speed = sum(s["speed_kph"] for s in c_samples) / len(c_samples)
            p_full_throttle = (
                sum(1 for s in p_samples if s["throttle_pct"] >= 95.0)
                / len(p_samples)
                * 100.0
            )
            c_full_throttle = (
                sum(1 for s in c_samples if s["throttle_pct"] >= 95.0)
                / len(c_samples)
                * 100.0
            )
            p_lap_t = primary.get("lap_time_s")
            c_lap_t = comparison.get("lap_time_s")
            lap_delta_s = (
                round(float(p_lap_t) - float(c_lap_t), 3)
                if isinstance(p_lap_t, (int, float)) and isinstance(c_lap_t, (int, float))
                else None
            )
            delta_summary = {
                "primary_driver": primary["code"],
                "comparison_driver": comparison["code"],
                "max_speed_delta_kph": round(
                    float(primary.get("max_speed_kph") or 0.0)
                    - float(comparison.get("max_speed_kph") or 0.0),
                    1,
                ),
                "avg_speed_delta_kph": round(p_avg_speed - c_avg_speed, 1),
                "primary_avg_speed_kph": round(p_avg_speed, 1),
                "comparison_avg_speed_kph": round(c_avg_speed, 1),
                "primary_full_throttle_pct": round(p_full_throttle, 1),
                "comparison_full_throttle_pct": round(c_full_throttle, 1),
                "lap_time_delta_s": lap_delta_s,
            }

    session_meta = payload.get("session", {})
    return {
        "year": int(session_meta.get("year", 2025)),
        "round_number": int(session_meta.get("round_number", 1)),
        "session_type": str(session_meta.get("session_type", "R")),
        "mode": primary["mode"],
        "primary": primary,
        "comparison": comparison,
        "delta_summary": delta_summary,
    }
