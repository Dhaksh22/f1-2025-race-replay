from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

import httpx

from backend.app.core.config import settings
from backend.app.schemas.session import ChatMessage, ChatResponse, ChatSource
from backend.app.services.race_data import (
    DRIVER_ROSTER_2025,
    SessionUnavailableError,
    load_replay_payload,
)
from backend.app.services.retrieval import KnowledgeDocument, retriever
from backend.app.services.telemetry import compare_driver_telemetry
from src.lib.season import SUPPORTED_SEASON, require_2025_year
from src.lib.time import format_time

KNOWN_DRIVER_CODES = {d["code"] for d in DRIVER_ROSTER_2025}
NAME_TO_CODE = {
    d["full_name"].split()[-1].lower(): d["code"] for d in DRIVER_ROSTER_2025
}
NAME_TO_CODE.update({d["code"].lower(): d["code"] for d in DRIVER_ROSTER_2025})


def detect_mentioned_drivers(
    message: str, selected_drivers: Optional[List[str]] = None
) -> List[str]:
    found: List[str] = []
    tokens = re.findall(r"[A-Za-z]+", message or "")
    for tok in tokens:
        upper = tok.upper()
        low = tok.lower()
        if upper in KNOWN_DRIVER_CODES and upper not in found:
            found.append(upper)
        elif low in NAME_TO_CODE and NAME_TO_CODE[low] not in found:
            found.append(NAME_TO_CODE[low])

    for drv in selected_drivers or []:
        code = str(drv).upper().strip()
        if code and code not in found:
            found.append(code)
    return found


def detect_non_2025_year_request(message: str, requested_year: int = 2025) -> Optional[int]:
    if requested_year != SUPPORTED_SEASON:
        return requested_year
    years = [int(y) for y in re.findall(r"\b(19\d{2}|20\d{2})\b", message or "")]
    for y in years:
        if y != SUPPORTED_SEASON:
            return y
    return None


def gather_session_context_evidence(
    payload: Optional[Dict[str, Any]],
    message: str,
    mentioned_drivers: List[str],
    current_lap: Optional[int] = None,
) -> Tuple[List[str], List[str], List[str]]:
    """
    Backend tool function that inspects a loaded 2025 session payload and returns:
    (verified_session_facts, calculated_metrics, uncertainties)
    Never fabricates missing telemetry, lap times, pit stops, or incidents.
    """
    verified: List[str] = []
    metrics: List[str] = []
    uncertainties: List[str] = []

    if not payload:
        uncertainties.append(
            "No 2025 session telemetry is currently loaded for this query; session-specific lap times, pit stops, and telemetry cannot be verified."
        )
        return verified, metrics, uncertainties

    session_meta = payload.get("session", {})
    event_name = session_meta.get("event_name", "2025 Grand Prix")
    session_type = session_meta.get("session_type", "R")
    round_num = session_meta.get("round_number", 1)
    total_laps = session_meta.get("total_laps")
    data_source = session_meta.get("data_source", "fastf1")

    verified.append(
        f"Session: 2025 Round {round_num} — {event_name} ({session_type}), Total Laps: {total_laps or 'N/A'}."
    )
    if data_source == "fallback_demo":
        uncertainties.append(
            "Note: This session is currently using the deterministic 2025 fallback profile because cached/live FastF1 telemetry was not present on disk."
        )

    frames = payload.get("frames", [])
    lap_summaries = payload.get("lap_summaries", {}).get("drivers", {})
    strategies_by_code = {
        s["code"]: s for s in payload.get("strategies", []) if "code" in s
    }
    rc_messages = payload.get("race_control_messages", [])
    track_statuses = payload.get("track_status", []) or payload.get("track_statuses", [])

    # Check if user asked about a driver not in this session
    session_driver_codes = {
        d["code"] for d in session_meta.get("drivers", []) if "code" in d
    }
    if not session_driver_codes and frames:
        session_driver_codes = set(frames[0].get("drivers", {}).keys())

    target_drivers = [d for d in mentioned_drivers if d in session_driver_codes]
    missing_drivers = [d for d in mentioned_drivers if d not in session_driver_codes]
    for md in missing_drivers:
        uncertainties.append(
            f"Driver '{md}' does not have recorded telemetry in the selected {event_name} ({session_type}) session."
        )

    if not target_drivers and frames:
        # Default to top 2 drivers in current/final frame
        last_f = frames[-1]
        sorted_codes = sorted(
            last_f.get("drivers", {}).keys(),
            key=lambda c: last_f["drivers"][c].get("position", 99),
        )
        target_drivers = sorted_codes[:2]

    # 1. Driver positions, lap times, and tyre strategy facts
    for code in target_drivers[:3]:
        strat = strategies_by_code.get(code)
        if strat:
            stint_desc = ", ".join(
                f"Stint {st['stint_number']}: {st['compound']} (Laps {st['start_lap']}–{st['end_lap']}, {st['lap_count']} laps)"
                for st in strat.get("stints", [])
            )
            pos_str = f"P{strat['position']}" if strat.get("position") else "classified"
            verified.append(
                f"{code} ({pos_str}) completed {strat.get('pit_stops', 0)} pit stop(s): {stint_desc or 'no stint records'}."
            )
            deg = strat.get("degradation")
            if deg:
                metrics.append(
                    f"{code} Bayesian Tyre Model: {deg.get('compound')} health {deg.get('health_pct')}% "
                    f"(expected pace delta +{deg.get('expected_delta_s')}s/lap, deg rate {deg.get('degradation_rate_s_per_lap')}s/lap)."
                )

        drv_laps = lap_summaries.get(code)
        if drv_laps:
            best_s = drv_laps.get("best_lap_s")
            theo_s = drv_laps.get("theoretical_best_s")
            laps_list = drv_laps.get("laps", [])
            valid_times = [
                l["time_s"]
                for l in laps_list
                if isinstance(l.get("time_s"), (int, float)) and l["time_s"] > 0
            ]
            if best_s:
                verified.append(f"{code} fastest recorded lap: {format_time(best_s)} ({best_s:.3f}s).")
            if valid_times:
                avg_s = sum(valid_times) / len(valid_times)
                metrics.append(
                    f"{code} average lap pace across {len(valid_times)} timed laps: {format_time(avg_s)} ({avg_s:.3f}s)"
                    + (f", theoretical optimal lap: {format_time(theo_s)} ({theo_s:.3f}s)." if theo_s else ".")
                )

    # 2. Multi-driver telemetry & pace comparison
    if len(target_drivers) >= 2:
        d1, d2 = target_drivers[0], target_drivers[1]
        comp = compare_driver_telemetry(
            payload=payload,
            primary_driver=d1,
            compare_driver=d2,
            mode="lap",
            lap=current_lap,
        )
        delta = comp.get("delta_summary")
        if delta:
            metrics.append(
                f"Telemetry comparison ({d1} vs {d2} on Lap {comp['primary'].get('lap')}): "
                f"Top speed delta {delta['max_speed_delta_kph']:+.1f} km/h, "
                f"Average speed delta {delta['avg_speed_delta_kph']:+.1f} km/h "
                f"({d1}: {delta['primary_avg_speed_kph']} km/h vs {d2}: {delta['comparison_avg_speed_kph']} km/h), "
                f"Full-throttle application {delta['primary_full_throttle_pct']}% vs {delta['comparison_full_throttle_pct']}%."
            )

    # 3. Safety Car, VSC, and Race Control facts
    sc_periods = [
        st for st in track_statuses if str(st.get("status")) in ("4", "5", "6", "7")
    ]
    if sc_periods:
        for st in sc_periods:
            label = st.get("label") or ("SC" if str(st.get("status")) == "4" else "VSC")
            s_lap = st.get("start_lap")
            e_lap = st.get("end_lap")
            lap_span = f" (Laps {s_lap}–{e_lap})" if s_lap and e_lap else ""
            verified.append(
                f"Track Status {label} active from {st.get('start_time', 0):.1f}s to {st.get('end_time') or 'end'}s{lap_span}."
            )
    else:
        verified.append("No Safety Car or Red Flag periods were recorded in the track status log for this session.")

    if rc_messages:
        notable_rc = [
            m for m in rc_messages
            if m.get("category") in ("SafetyCar", "Flag") or "PENALTY" in m.get("message", "").upper()
        ][:4]
        for msg in notable_rc:
            verified.append(f"Race Control [{msg['time']:.1f}s]: {msg['message']}")
    else:
        uncertainties.append(
            "Detailed FIA Race Control text messages are not present in this session payload."
        )

    q_lower = (message or "").lower()
    if any(w in q_lower for w in ("lose position", "lost position", "overtake", "why did", "incident", "crash", "penalty")):
        uncertainties.append(
            "Hypothesis note: While position changes, pit windows, and lap-time deltas are verified from telemetry, "
            "exact on-track wheel-to-wheel causes (e.g., lock-ups, steward deliberations, or minor bodywork damage) "
            "cannot be proven from telemetry coordinates alone without steward decision documents."
        )

    return verified, metrics, uncertainties


def answer_f1_question(req: ChatMessage) -> ChatResponse:
    """
    Main entrypoint for the Formula 1 Knowledge & Session Strategist Chatbot.
    Enforces 2025 season restriction, retrieves trusted FIA/F1 documents, executes
    session-context tools, and returns a structured, citation-backed response.
    """
    clean_msg = (req.message or "").strip()
    if not clean_msg:
        raise ValueError("Chat message cannot be empty.")
    if len(clean_msg) > settings.max_chat_input_chars:
        raise ValueError(
            f"Chat message exceeds maximum length of {settings.max_chat_input_chars} characters."
        )

    # 1. Check for non-2025 season requests
    non_2025 = detect_non_2025_year_request(clean_msg, req.year)
    docs = retriever.retrieve(clean_msg, top_k=3)
    source_details = [
        ChatSource(
            title=d.title,
            url=d.url,
            source_org=d.source_org,
            retrieval_date=d.retrieval_date,
            category=d.category,
        )
        for d in docs
    ]
    sources_str = [f"{d.title} ({d.url})" for d in docs]
    general_knowledge = [d.content for d in docs]

    if non_2025 is not None and req.year != SUPPORTED_SEASON:
        # Strict validation when request year is not 2025
        require_2025_year(req.year)

    payload: Optional[Dict[str, Any]] = None
    uncertainties: List[str] = []

    if non_2025 is not None:
        uncertainties.append(
            f"Season Restriction: This application's race-data and telemetry tools are strictly restricted to the "
            f"{SUPPORTED_SEASON} Formula 1 season. Session telemetry for {non_2025} cannot be loaded."
        )
    elif req.round_number is not None:
        try:
            year_checked = require_2025_year(req.year)
            payload = load_replay_payload(
                year_checked,
                int(req.round_number),
                req.session_type or "R",
            )
        except SessionUnavailableError as exc:
            uncertainties.append(f"Selected 2025 session data is currently unavailable: {exc}")
        except ValueError as exc:
            uncertainties.append(f"Session parameter notice: {exc}")

    mentioned = detect_mentioned_drivers(clean_msg, req.selected_drivers)
    verified_facts, calc_metrics, tool_uncertainties = gather_session_context_evidence(
        payload=payload,
        message=clean_msg,
        mentioned_drivers=mentioned,
        current_lap=req.current_lap,
    )
    uncertainties.extend(tool_uncertainties)

    # 2. If an external LLM API key is configured, attempt grounded LLM generation with fallback
    if settings.is_llm_configured:
        llm_answer = _call_external_llm(
            question=clean_msg,
            verified_facts=verified_facts,
            calc_metrics=calc_metrics,
            general_knowledge=general_knowledge,
            uncertainties=uncertainties,
        )
        if llm_answer:
            return ChatResponse(
                answer=llm_answer,
                sources=sources_str,
                source_details=source_details,
                verified_session_facts=verified_facts,
                calculated_metrics=calc_metrics,
                general_f1_knowledge=general_knowledge,
                uncertainties=uncertainties,
                suggested_followups=_build_followups(mentioned, req.round_number),
                model=settings.llm_model,
                provider_mode="llm_api",
            )

    # 3. Deterministic, grounded local RAG + Session Synthesizer (works without API key)
    synthesized = _synthesize_grounded_response(
        question=clean_msg,
        verified_facts=verified_facts,
        calc_metrics=calc_metrics,
        general_knowledge=general_knowledge,
        uncertainties=uncertainties,
        non_2025=non_2025,
    )

    return ChatResponse(
        answer=synthesized,
        sources=sources_str,
        source_details=source_details,
        verified_session_facts=verified_facts,
        calculated_metrics=calc_metrics,
        general_f1_knowledge=general_knowledge,
        uncertainties=uncertainties,
        suggested_followups=_build_followups(mentioned, req.round_number),
        model="f1-rag-grounded-v1",
        provider_mode="local_rag_synthesizer",
    )


def _synthesize_grounded_response(
    question: str,
    verified_facts: List[str],
    calc_metrics: List[str],
    general_knowledge: List[str],
    uncertainties: List[str],
    non_2025: Optional[int] = None,
) -> str:
    sections: List[str] = []

    if non_2025 is not None:
        sections.append(
            f"**2025 Season Restriction Notice:** Session telemetry tools are restricted exclusively to the **2025 Formula 1 season**, "
            f"so raw session data for **{non_2025}** will not be loaded. Below is the relevant general Formula 1 regulation and reference context."
        )

    if verified_facts:
        facts_bullets = "\n".join(f"- {f}" for f in verified_facts)
        sections.append(f"**Verified 2025 Session Facts:**\n{facts_bullets}")

    if calc_metrics:
        metrics_bullets = "\n".join(f"- {m}" for m in calc_metrics)
        sections.append(f"**Calculated Telemetry & Pace Metrics:**\n{metrics_bullets}")

    if general_knowledge:
        sections.append(f"**Formula 1 Sporting & Technical Reference:**\n{general_knowledge[0]}")

    if uncertainties:
        unc_bullets = "\n".join(f"- {u}" for u in uncertainties)
        sections.append(f"**Limitations & Evidence Scope:**\n{unc_bullets}")

    return "\n\n".join(sections)


def _call_external_llm(
    question: str,
    verified_facts: List[str],
    calc_metrics: List[str],
    general_knowledge: List[str],
    uncertainties: List[str],
) -> Optional[str]:
    system_prompt = (
        "You are an expert Formula 1 Race Engineer and FIA Regulations Analyst for the 2025 Formula 1 season. "
        "Strictly distinguish between: (1) Verified Session Facts, (2) Calculated Metrics, (3) General F1 Knowledge, "
        "and (4) Hypotheses/Uncertainties. NEVER invent lap times, pit stops, penalties, race control messages, or telemetry."
    )
    user_context = (
        f"Question: {question}\n\n"
        f"Verified Session Facts:\n" + "\n".join(f"- {x}" for x in verified_facts) + "\n\n"
        f"Calculated Metrics:\n" + "\n".join(f"- {x}" for x in calc_metrics) + "\n\n"
        f"Trusted F1 Knowledge:\n" + "\n".join(f"- {x}" for x in general_knowledge) + "\n\n"
        f"Uncertainties / Missing Evidence:\n" + "\n".join(f"- {x}" for x in uncertainties)
    )
    try:
        headers = {
            "Authorization": f"Bearer {settings.llm_api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": settings.llm_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_context},
            ],
            "temperature": 0.1,
            "max_tokens": 600,
        }
        with httpx.Client(timeout=settings.llm_timeout_seconds) as client:
            resp = client.post(
                f"{settings.llm_base_url.rstrip('/')}/chat/completions",
                headers=headers,
                json=payload,
            )
            if resp.status_code == 200:
                data = resp.json()
                return data["choices"][0]["message"]["content"]
    except Exception as exc:
        print(f"Warning: External LLM provider call failed, using local grounded synthesizer: {exc}")
    return None


def _build_followups(mentioned_drivers: List[str], round_number: Optional[int]) -> List[str]:
    d1 = mentioned_drivers[0] if len(mentioned_drivers) >= 1 else "NOR"
    d2 = mentioned_drivers[1] if len(mentioned_drivers) >= 2 else "VER"
    return [
        f"Compare {d1} and {d2}'s pace and telemetry.",
        f"What was the tyre strategy and degradation for {d1}?",
        "Explain the Safety Car and VSC phases in this session.",
        "How do DRS detection and activation rules work in 2025?",
    ]
