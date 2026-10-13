# F1 Race Replay Web Migration Plan (File-Level Architecture & Phased Plan)

## 1. Repository Inspection Summary

The existing repository is a single-process desktop Python application built around FastF1 telemetry, Arcade (OpenGL 2D rendering), and PySide6 (Qt secondary insight windows and session selection GUI).

### File-by-File Audit of Existing Codebase

| File / Module | Existing Responsibility | UI / Desktop Coupling | Migration Disposition |
|---|---|---|---|
| `main.py` | CLI/GUI entrypoint, dispatches to Arcade replay & Qt insight processes | Coupled to `PySide6` & `Arcade` | **Keep intact** for desktop compatibility; replace orchestration in web mode with `backend/app/main.py` |
| `src/f1_data.py` | FastF1 session fetching, `_process_single_driver`, `get_race_telemetry`, `get_quali_telemetry`, `get_practice_telemetry`, `_compute_safety_car_positions`, `get_live_standings` | **Independent** of Arcade/PySide6 | **Reuse directly** via backend adapter (`backend/app/services/race_data.py`) |
| `src/lib/season.py` | Season helper and `require_2025_year()` | **Independent** | **Reuse directly** across backend API, data loaders, and chatbot tools |
| `src/lib/tyres.py` | Compound string ↔ integer mapping (`SOFT=0`..`WET=4`) | **Independent** | **Reuse directly** |
| `src/lib/time.py` | `format_time()` and `parse_time_string()` | **Independent** | **Reuse directly** |
| `src/lib/sectors.py` | Sector bests (`best_sectors`, `theoretical_best_s`, `classify_sector_statuses`, `session_best_holders`) | **Independent** | **Reuse directly** in backend lap/sector analytics |
| `src/lib/settings.py` | JSON settings manager (`cache_location`, `computed_data_location`) | **Independent** | **Reuse directly** |
| `src/bayesian_tyre_model.py` | `BayesianTyreDegradationModel` state-space tyre degradation & track abrasion | **Independent** (`numpy`, `pandas`, `scipy`) | **Reuse directly** in backend strategy service |
| `src/tyre_degradation_integration.py` | `TyreDegradationIntegrator` wrapper around Bayesian model | **Independent** | **Reuse directly** in backend strategy service |
| `src/ui_components.py` | Arcade UI widgets + `build_track_from_example_lap`, `plotDRSzones`, `extract_race_events` | Imports `arcade` at top-level | **Extract** pure math/geometry helpers (`build_track_from_example_lap`, `plotDRSzones`, `extract_race_events`) into Arcade-free `backend/app/services/replay.py`; replace UI components in React |
| `src/interfaces/race_replay.py` | `F1RaceReplayWindow` (Arcade renderer, world-to-screen rotation/scaling, `_compute_lap_times`, `_compute_status_laps`) | Imports `arcade` at top-level | **Extract** `_compute_lap_times` & `_compute_status_laps` into `backend/app/services/replay.py`; reimplement circuit canvas & HUD in React (`CircuitCanvas.tsx`) |
| `src/interfaces/qualifying.py` | Qualifying segment replay & telemetry chart window | Coupled to `arcade` | Reimplement in React (`TelemetryPanel.tsx` & `CircuitCanvas.tsx`) |
| `src/interfaces/practice.py` | Practice session replay & comparison telemetry | Coupled to `arcade` | Reimplement in React (`TelemetryPanel.tsx` & `CircuitCanvas.tsx`) |
| `src/services/stream.py` | Local TCP socket server/client (`localhost:9999`) with `QThread` | Coupled to `PySide6.QtCore` | **Replace** in web mode with FastAPI WebSocket (`/ws/replay/{year}/{round_number}`) + HTTP polling fallback |
| `src/insights/driver_telemetry_window.py` | Stacked Speed, Gear, Throttle/Brake Matplotlib Qt window | Coupled to `PySide6` & `matplotlib` | **Replace** with interactive web charts (`TelemetryPanel.tsx`) |
| `src/insights/lap_time_chart_window.py` | Lap time evolution, SC/VSC bands, 3-lap moving average, gap mode | Coupled to `PySide6` & `matplotlib` | **Replace** with web lap-time evolution chart (`LapSectorPanel.tsx`) |
| `src/insights/sector_times_window.py` | Purple/green sector table & ideal lap summary | Coupled to `PySide6` | **Replace** with web sector timing table (`LapSectorPanel.tsx`) |
| `src/insights/tyre_strategy_window.py` | Horizontal driver stint bars by compound | Coupled to `PySide6` | **Replace** with web strategy view (`TyreStrategyPanel.tsx`) |
| `src/insights/race_control_feed_window.py` | Chronological FIA race control feed synced to replay clock | Coupled to `PySide6` | **Replace** with web race control feed (`RaceControlPanel.tsx`) |
| `src/insights/track_position_window.py` | Real circuit vs circular schematic position map | Coupled to `PySide6` | **Replace** with web schematic toggle (`TrackPositionSchematic.tsx`) |

---

## 2. Layered Web Architecture

1. **Browser Frontend (`frontend/`)**:
   - React 18 + TypeScript + Vite + Tailwind CSS.
   - HTML5 Canvas circuit renderer (`CircuitCanvas.tsx`) preserving exact coordinate rotation (`circuit_rotation`), inner/outer track boundaries, DRS zones, checkered start/finish line, normal-offset driver labels, and pulsing approximated Safety Car marker.
   - Modular analytics panels for Leaderboard/HUD/Weather/Standings, Telemetry Comparison, Lap & Sector Timing, Tyre Strategy & Bayesian Degradation, Race Control & Track Schematic.
   - Collapsible F1 AI Knowledge & Session Strategist Chatbot (`ChatSidebar.tsx`).
2. **Backend API (`backend/app/api/`)**:
   - FastAPI REST endpoints for metadata, replay bootstrap, paginated frame chunks, leaderboard snapshots, driver telemetry comparisons, tyre strategy, lap/sector analysis, race control, and chatbot queries.
   - WebSocket endpoint (`/ws/replay/{year}/{round_number}`) for low-latency incremental frame streaming with server/client playback synchronization (`play`, `pause`, `seek`, `set_speed`, `reset`).
3. **Reusable Race-Data & Replay Adapter (`backend/app/services/race_data.py`, `replay.py`, `telemetry.py`)**:
   - Wraps `src/f1_data.py`, `src/lib/sectors.py`, `src/lib/tyres.py`, and `src/tyre_degradation_integration.py` without importing `arcade` or `PySide6`.
   - Converts NumPy arrays, pandas DataFrames, and FastF1 objects into clean, JSON-serializable Pydantic models.
4. **Processed-Data & Cache Layer (`data/processed/`, `computed_data/`, `.fastf1-cache/`)**:
   - Preserves FastF1 HTTP SQLite cache (`.fastf1-cache`) and desktop pickle cache (`computed_data/`).
   - Stores versioned, compressed JSON processed payloads (`data/processed/v1_2025_R{round}_{session_type}.json.gz`) keyed by season (`2025`), round, and session type.
5. **F1 Knowledge Chatbot & RAG Layer (`backend/app/services/retrieval.py`, `chatbot.py`)**:
   - Lightweight local BM25/TF-IDF index over curated official FIA 2025 Sporting & Technical Regulations, flag rules, Safety Car/VSC procedures, Pirelli tyre rules, DRS rules, and 2025 circuit/team reference material with source URLs and retrieval dates.
   - Session-grounded backend tools that query verified 2025 session data and explicitly separate `verified_session_facts`, `calculated_metrics`, `general_f1_knowledge`, and `uncertainties`.

---

## 3. Execution Phases

- **Phase 1**: Repository inspection and file-level migration plan (Completed).
- **Phase 2**: Extract and adapt Arcade-free replay, track geometry, lap/sector, and tyre degradation services with 2025 season enforcement and versioned caching.
- **Phase 3**: Complete FastAPI schemas, REST endpoints, and WebSocket replay streaming server.
- **Phase 4**: Scaffold React + TypeScript + Vite + Tailwind frontend and implement the interactive Canvas circuit replay with play, pause, seek, speed control, WebSocket streaming, and HTTP fallback.
- **Phase 5**: Implement Leaderboard/HUD/Weather/Standings, Telemetry charts, Lap & Sector analysis, Tyre Strategy & Bayesian degradation, Race Control feed, and Track Position schematic views.
- **Phase 6**: Implement the F1 Knowledge Chatbot with RAG retrieval, 2025 session context tools, and collapsible frontend chat panel.
- **Phase 7**: Add comprehensive automated unit/integration tests, `.env.example`, and production build configuration.
- **Phase 8**: Update `README.md`, `docs/ARCHITECTURE.md`, and `MIGRATION_REPORT.md`, and verify all tests and builds.
