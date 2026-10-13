# Formula 1 Race Replay Web Platform — Migration Report

## Executive Summary

The **F1 Race Replay** project has been migrated from a desktop-only application (Arcade/PySide6) into a lightweight, responsive, full-stack web platform strictly restricted to the **2025 Formula 1 season**.

The existing desktop architecture, data structures, telemetry mathematics, Bayesian tyre degradation model, and race-control insights have been preserved and decoupled into pure Python processing services exposed via a FastAPI REST & WebSocket backend, paired with a React 18 + TypeScript + Vite + Tailwind CSS pit-wall frontend.

---

## 1. Preserved Components and Logic

| Component | Source File(s) | Preserved Logic & Functionality |
|---|---|---|
| **Track Geometry** | `src/f1_data.py`, `src/ui_components.py` | Coordinate rotation, inner/outer track boundaries, circuit length calculation, checkered start/finish line geometry, and DRS zones extraction. |
| **Safety Car Approximation** | `src/interfaces/race_replay.py` | Deterministic approximation ahead of the race leader from official FIA track status timestamps; explicitly labeled as simulated in the UI and schemas. |
| **Live Standings & Intervals** | `src/ui_components.py`, `src/f1_data.py` | Gap-to-Leader (`L`) and Interval-to-Car-Ahead (`I`) formulas, driver team colors, position ordering. |
| **Sector Timing** | `src/lib/sectors.py`, `src/lib/time.py` | F1 sector status benchmark detection (`SESSION_BEST` purple, `PERSONAL_BEST` green, yellow), ideal lap calculations. |
| **Bayesian Tyre Degradation** | `src/bayesian_tyre_model.py`, `src/tyre_degradation_integration.py` | Compound wear rates, health score (%), pace delta penalty, overdriving detection, and cliff lap prediction. |
| **FIA Race Control** | `src/f1_data.py`, `src/run_session.py` | Chronological race control messages, flag statuses, track status periods. |
| **Desktop Application** | `main.py`, `src/gui/`, `src/interfaces/` | Left untouched and intact. Desktop users can continue running `python main.py`. |

---

## 2. Replaced & Newly Created Components

| Replaced Desktop Component | New Web Architecture Component | Rationale & Implementation Details |
|---|---|---|
| `arcade.Window` (`F1RaceReplayWindow`) | `frontend/src/features/replay/CircuitCanvas.tsx` | HTML5 Canvas hardware-accelerated circuit renderer; supports both Real Rotated Circuit Geometry and Circular Track Position Ring modes. |
| PySide6 Telemetry Window (`driver_telemetry_window.py`) | `frontend/src/features/telemetry/TelemetryPanel.tsx` | Interactive Speed, Throttle, Brake, Gear, and DRS SVG charts with multi-driver delta metrics and qualifying/practice support. |
| PySide6 Sector Analysis (`sector_analysis.py`) | `frontend/src/features/telemetry/LapSectorPanel.tsx` | Interactive sector timing history table with purple/green highlights and theoretical ideal lap benchmarks. |
| PySide6 Pit Strategy (`pit_wall_view.py`) | `frontend/src/features/strategy/TyreStrategyPanel.tsx` | Horizontal driver tyre stint timelines and Bayesian tyre degradation health cards. |
| PySide6 Telemetry Stream (`stream.py`) | `backend/app/api/routes.py` (`websocket_replay_endpoint`) & `frontend/src/services/replaySocket.ts` | Zero-dependency async WebSocket streaming engine with adaptive frame pacing, seeking, and HTTP chunked polling fallback. |
| N/A (New Feature) | `backend/app/services/retrieval.py` & `backend/app/services/chatbot.py` & `frontend/src/features/chat/ChatSidebar.tsx` | FIA Grounded Formula 1 Knowledge & Session Strategist Chatbot with anti-hallucination evidence separation. |

---

## 3. Centralized 2025 Season Restriction

1. **Backend Validation**: `require_2025_year()` enforces `year == 2025` on all API endpoints (`/api/events`, `/api/sessions/2025/...`, `/api/ws/replay/2025/...`, and `/api/chat`). Requests for non-2025 seasons return HTTP 400.
2. **Frontend UI**: UI displays a locked "2025 SEASON ONLY" badge, restricting selection exclusively to the 24 official 2025 FIA World Championship Grands Prix.
3. **Chatbot Tools**: Refuses to load telemetry from non-2025 seasons (e.g., 2021, 2024), explicitly citing the 2025 season boundary in the response uncertainties.
4. **Cache Partitioning**: Processed files are versioned and season-scoped: `v1_2025_R{round}_{session}.json.gz`.

---

## 4. Performance & Caching Strategy

- **Processed Data Cache**: Processed replay payloads are compressed into `.json.gz` files inside `data/processed/`. Subsequent loads complete in <15ms without recomputing telemetry or calling FastF1.
- **Cache Invalidation**: Supported via `DELETE /api/sessions/2025/{round}/cache?session_type={type}` and the frontend Refresh button.
- **No Heavy Infrastructure**: Uses standard Python + Node libraries without requiring Redis, Docker, or external databases.
- **Client Frame Optimization**: Replay frames use relative offsets and normalized numbers; tab-switching automatically pauses playback to conserve client CPU and memory.

---

## 5. Verification & Test Results

- **Automated Backend Tests (`tests/test_backend_migration.py`)**: 19 tests executed across all 11 required areas. **Result: 19 passed, 0 failed (100% pass rate in 6.51s).**
- **Frontend Production Build (`frontend/`)**: Compiled with TypeScript `tsc -b` and Vite `vite build`. **Result: Zero build errors; static assets generated in `frontend/dist/`.**
