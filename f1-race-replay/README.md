# F1 Race Replay 🏎️ 🏁 (2025 Web Platform & Desktop Engine)

A Formula 1 race replay, telemetry analytics, and FIA knowledge platform strictly restricted to the **2025 Formula 1 season**, available as both a lightweight modern web application and the original desktop application.

![Web Pit-Wall Replay Preview](./resources/preview.png)

---

## 🌟 2025 Web Platform Capabilities

1. **Strict 2025 Season Lock:** Centralized season boundary across API endpoints, data loaders, versioned caches, and chatbot tools. Selection is restricted to all 24 official 2025 FIA World Championship Grands Prix.
2. **Interactive HTML5 Canvas Circuit Replay:**
   - Real rotated circuit geometry with asphalt road surface, inner and outer track boundaries, checkered start/finish line, and emerald green DRS zones.
   - Dual visualization modes: **Real Circuit Geometry** and **Circular Track Position Ring** (migrated from `driver_track_positions.py`).
   - Driver markers styled in official team colors with normal-offset 3-letter driver badges and selection rings.
   - **Simulated Safety Car Visualization:** Pulsing amber marker explicitly labeled `SC (APPROXIMATED)` deployed mathematically ahead of the race leader based on official FIA track-status timestamps.
3. **Smooth Playback Engine:**
   - Play/pause, step forward/back, adjustable playback speed (0.25x to 32x), reset to start.
   - Interactive timeline scrubber with event flags for Safety Car, VSC, Yellow Flag, Red Flag, and DNF incidents.
   - Zero-dependency WebSocket streaming (`/api/ws/replay/2025/{round}`) with automatic fallback to local client interpolation and chunked HTTP retrieval.
   - Smart background throttling: pauses playback automatically when the browser tab is hidden to save CPU/battery.
4. **Live Leaderboard & Timing Tower:**
   - Real-time driver standings with interactive toggle between **Gap to Leader (`L`)** and **Interval to Car Ahead (`I`)**.
   - Pirelli tyre compound badges (Soft, Medium, Hard, Intermediate, Wet) with current stint age.
   - In-pit / out-lap indicators, retirements (OUT/DNF), speed trap, and live FIA championship points awarded.
   - Integrated Weather HUD: track temperature, ambient temperature, humidity, and rain status.
5. **Interactive Telemetry Comparison Traces:**
   - Multi-driver comparative traces for Speed (km/h), Throttle (%), Brake (%), Gear (1–8), and DRS activation.
   - Supports Race Laps, Rolling 30s Time Windows, Qualifying Segments (Q1/Q2/Q3), and Practice Best Laps.
   - Real-time delta summaries (Δ Speed, Δ Lap time).
6. **Official F1 Sector Timing & Ideal Lap Benchmarks:**
   - Lap-by-lap sector timing table with authentic F1 **Purple** (overall session best), **Green** (personal best), and Yellow highlights.
   - Ideal theoretical lap calculation and session sector records.
7. **Pirelli Tyre Strategy & Bayesian Degradation:**
   - Horizontal driver tyre stint timelines illustrating pit stop windows.
   - Bayesian tyre degradation health cards: health score (%), pace penalty delta (+s/lap), wear rate, overdriving/sliding detection, and cliff lap prediction.
8. **FIA Race Control Stream:**
   - Chronological official FIA race control messages and track status period logs with jump-to-time scrubbing.
9. **Formula 1 Knowledge & Session Strategist AI Chatbot:**
   - Built-in grounded RAG assistant trained on official FIA 2025 sporting and technical regulations.
   - Contextual understanding of the selected 2025 session and driver pace.
   - Anti-hallucination structure: separates Verified Session Facts, Calculated Metrics, General F1 Knowledge, Scope Limitations / Uncertainties, and FIA Citations.
   - Refuses to fabricate unrecorded telemetry (e.g. internal tire core temps, unbroadcast radio) or load non-2025 seasons.

---

## 🚀 Quickstart: Web Platform

### Prerequisites
- Python 3.11+
- Node.js 18+ & npm

### 1. Start the FastAPI Web Backend
```bash
# In repository root:
pip install -r requirements.txt

# Start FastAPI server on port 8000:
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```
API Documentation will be available at [http://localhost:8000/docs](http://localhost:8000/docs).

### 2. Start the React Frontend
```bash
cd frontend
npm install
npm run dev
```
Open your browser at [http://localhost:5173](http://localhost:5173).

To build the static frontend for production:
```bash
cd frontend
npm run build
```
Static assets will be compiled into `frontend/dist/`.

---

## 🖥️ Desktop Application (Preserved)

The original desktop experience powered by Arcade and PySide6 remains functional:

```bash
# Run the desktop replay interface
python main.py
```

### Desktop Keyboard Controls
- **Pause/Resume:** `SPACE`
- **Rewind/Fast Forward:** `←` / `→`
- **Playback Speed:** `↑` / `↓` or keys `1`–`4`
- **Restart:** `R`
- **Toggle DRS Zones:** `D`
- **Toggle Driver Names:** `L`
- **Toggle Progress Bar:** `B`

---

## 🧪 Automated Testing

Run the comprehensive test suite verifying the 2025 season lock, API schemas, replay frame ordering, WebSocket streaming, telemetry, strategy, and grounded chatbot:

```bash
python -m pytest tests/test_backend_migration.py -v
```

---

## ⚙️ Configuration & Environment Variables

Copy `.env.example` to `.env` to customize settings:

| Variable | Default | Description |
|---|---|---|
| `PORT` | `8000` | Backend API port |
| `FRONTEND_ORIGIN` | `http://localhost:5173` | Allowed CORS frontend origin |
| `CACHE_DIR` | `.fastf1-cache` | FastF1 raw HTTP cache directory |
| `COMPUTED_DATA_DIR` | `computed_data` | Pre-computed desktop replay pickles directory |
| `PROCESSED_DATA_DIR` | `data/processed` | Reusable versioned, compressed `.json.gz` cache directory |
| `ALLOW_DEMO_FALLBACK` | `true` | Allows fast deterministic 2025 session simulation when telemetry is not yet downloaded |
| `PREFER_LIVE_FASTF1` | `false` | When true, attempts live download from Ergast/FastF1 servers |
| `LLM_API_KEY` | `""` | Optional external LLM API key (OpenAI/Anthropic compatible). Chatbot uses grounded local synthesizer if empty |
| `LLM_MODEL` | `gpt-4o-mini` | Chatbot model name |

---

## 📂 Project Structure

```text
├── backend/
│   └── app/
│       ├── main.py                  # FastAPI application entry point & CORS
│       ├── api/routes.py            # REST routes & WebSocket replay streaming
│       ├── core/config.py           # Application settings & environment parsing
│       ├── schemas/session.py       # Pydantic schemas (Season, Replay, Telemetry, Chat)
│       └── services/
│           ├── race_data.py         # 2025 calendar loader & versioned cache manager
│           ├── replay.py            # Arcade-free track geometry, leaderboard & SC logic
│           ├── telemetry.py         # Calibrated multi-driver telemetry extraction
│           ├── retrieval.py         # FIA 2025 regulations BM25 knowledge retriever
│           └── chatbot.py           # Grounded session context evidence & strategist
├── frontend/
│   ├── src/
│   │   ├── types/f1.ts              # Strict TypeScript models matching backend API
│   │   ├── services/
│   │   │   ├── api.ts               # HTTP client with error handling
│   │   │   └── replaySocket.ts      # WebSocket streaming client with fallback
│   │   ├── features/
│   │   │   ├── replay/              # CircuitCanvas, PlaybackControls, Leaderboard, RaceControl
│   │   │   ├── telemetry/           # TelemetryPanel, LapSectorPanel
│   │   │   ├── strategy/            # TyreStrategyPanel (Bayesian deg cards)
│   │   │   └── chat/                # ChatSidebar (AI Strategist)
│   │   ├── App.tsx                  # Master pit-wall dashboard
│   │   └── main.tsx                 # React entry point
│   └── dist/                        # Static production build
├── src/                             # Preserved desktop engine (f1_data.py, GUI, insights)
├── main.py                          # Preserved desktop launcher
├── docs/ARCHITECTURE.md             # System architecture & Mermaid diagrams
├── MIGRATION_REPORT.md              # Detailed migration audit report
└── tests/test_backend_migration.py  # Automated pytest verification suite
```
