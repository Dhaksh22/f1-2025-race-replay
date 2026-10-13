from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Dict, List, Set, Tuple


@dataclass(frozen=True)
class KnowledgeDocument:
    doc_id: str
    title: str
    category: str
    url: str
    source_org: str
    retrieval_date: str
    content: str
    keywords: Tuple[str, ...] = field(default_factory=tuple)


TRUSTED_F1_CORPUS: List[KnowledgeDocument] = [
    KnowledgeDocument(
        doc_id="fia_2025_sporting_regs_points",
        title="2025 FIA Formula 1 Sporting Regulations — Championship Points & Race Distance (Article 6)",
        category="Regulations",
        url="https://www.fia.com/regulation/category/110",
        source_org="FIA",
        retrieval_date="2025-02-26",
        keywords=("points", "scoring", "fastest lap", "sprint", "standings", "championship", "2025", "regulations"),
        content=(
            "Under the 2025 FIA Formula 1 Sporting Regulations, Grand Prix points are awarded to the top 10 classified "
            "finishers on a 25-18-15-12-10-8-6-4-2-1 scale. New for the 2025 season, the bonus point for setting the "
            "fastest lap of the race has been abolished. In Sprint sessions, points are awarded to the top 8 finishers "
            "on an 8-7-6-5-4-3-2-1 scale."
        ),
    ),
    KnowledgeDocument(
        doc_id="fia_2025_drs_rules",
        title="2025 FIA Formula 1 Sporting & Technical Regulations — Drag Reduction System (DRS)",
        category="Technical & Sporting Rules",
        url="https://www.fia.com/regulation/category/110",
        source_org="FIA",
        retrieval_date="2025-02-26",
        keywords=("drs", "drag reduction system", "overtaking", "wing", "detection", "activation", "1 second", "gap"),
        content=(
            "The Drag Reduction System (DRS) is an adjustable rear-wing flap designed to reduce aerodynamic drag and "
            "increase straight-line top speed (typically by 10–15 km/h) to aid overtaking. During a race, a driver may "
            "activate DRS in designated DRS activation zones only if they are within 1.000 second of the car ahead at "
            "the corresponding DRS detection point. Since 2024 and continuing in 2025, DRS is enabled after 1 completed "
            "lap (at the start of Lap 2) or 1 lap after a Safety Car restart, provided Race Control declares track "
            "conditions safe and dry."
        ),
    ),
    KnowledgeDocument(
        doc_id="fia_2025_safety_car_vsc",
        title="2025 FIA Formula 1 Sporting Regulations — Safety Car (SC) & Virtual Safety Car (VSC) Procedures (Articles 55–56)",
        category="Race Control & Safety Car",
        url="https://www.fia.com/regulation/category/110",
        source_org="FIA",
        retrieval_date="2025-02-26",
        keywords=("safety car", "sc", "vsc", "virtual safety car", "restart", "lapped cars", "unlap", "deploy", "track status"),
        content=(
            "A Safety Car (SC, Track Status 4) is deployed when there is a hazard on or near the track requiring the field "
            "to be neutralized behind the physical FIA Safety Car. Overtaking is prohibited, and all cars must queue behind "
            "the leader. Before a restart, lapped cars may be instructed by Race Control to unlap themselves. A Virtual "
            "Safety Car (VSC, Track Status 6/7) neutralizes the race without a physical car on track by requiring every "
            "driver to stay above a minimum reference time (roughly 30–40% slower) in every marshalling sector, preserving "
            "inter-car time gaps. Note: in F1 Race Replay, Safety Car coordinates are simulated ahead of the leader from "
            "official track status timestamps because official FIA feeds do not publish SC GPS telemetry."
        ),
    ),
    KnowledgeDocument(
        doc_id="fia_2025_flags_penalties",
        title="FIA International Sporting Code Appendix H & 2025 F1 Sporting Regulations — Flags & Penalties",
        category="Flags & Penalties",
        url="https://www.fia.com/regulation/category/123",
        source_org="FIA",
        retrieval_date="2025-02-26",
        keywords=("flag", "flags", "yellow", "red", "blue", "black", "penalty", "penalties", "5 second", "10 second", "track limits"),
        content=(
            "Official FIA flag signals in Formula 1: Green Flag (Track Status 1) indicates normal racing conditions; "
            "Single/Double Yellow Flag (Track Status 2) warns of danger on or near the track—drivers must reduce speed "
            "and must not overtake; Red Flag (Track Status 5) immediately suspends the session and requires cars to return "
            "to the pit lane; Blue Flag warns a lapped car to allow a faster lapping car to pass within three blue-flag "
            "panels; Black and White Flag is an unsportsmanlike conduct / track-limits warning (shown after 3 track-limit "
            "strikes); Black and Orange Flag orders a car with mechanical damage to pit for repairs. Standard time "
            "penalties imposed by the Stewards include 5-second, 10-second, drive-through, and 10-second stop-and-go penalties."
        ),
    ),
    KnowledgeDocument(
        doc_id="pirelli_2025_tyres_strategy",
        title="2025 Pirelli Formula 1 Tyre Compounds & Sporting Allocation Rules (Article 30)",
        category="Tyres & Pit Strategy",
        url="https://www.formula1.com/en/latest/article/f1-tires-explained",
        source_org="Formula 1 / Pirelli",
        retrieval_date="2025-03-01",
        keywords=("tyre", "tyres", "tire", "compound", "soft", "medium", "hard", "intermediate", "wet", "pit", "stint", "undercut", "overcut", "degradation"),
        content=(
            "At every 2025 Grand Prix, Pirelli nominates three dry slick compounds—Soft (Red, fastest initial grip, highest "
            "thermal/wear degradation), Medium (Yellow, balanced pace and durability), and Hard (White, lowest degradation, "
            "longest stint capability)—plus Green Intermediate (light standing water/damp) and Blue Full Wet (heavy rain). "
            "In a dry Grand Prix, every driver must use at least two different slick specifications (Article 30.5(m)), "
            "requiring at least one mandatory pit stop. Key strategic maneuvers include the undercut (pitting earlier than "
            "a rival to gain lap time on fresh tyres) and the overcut (staying out longer in clean air or hoping for a "
            "Safety Car/VSC cheap pit stop saving ~8–10 seconds)."
        ),
    ),
    KnowledgeDocument(
        doc_id="fia_2025_qualifying_sprint_format",
        title="2025 FIA Formula 1 Qualifying & Sprint Weekend Format",
        category="Session Formats",
        url="https://www.formula1.com/en/latest/article/everything-you-need-to-know-about-the-f1-sprint-format",
        source_org="Formula 1 / FIA",
        retrieval_date="2025-03-01",
        keywords=("qualifying", "q1", "q2", "q3", "sprint", "sq1", "sq2", "sq3", "format", "practice", "fp1", "fp2", "fp3"),
        content=(
            "A conventional 2025 F1 weekend features three 60-minute practice sessions (FP1, FP2, FP3), Qualifying "
            "(Q1: 18 min eliminating P16–P20; Q2: 15 min eliminating P11–P15; Q3: 12 min shootout for P1–P10), and the "
            "Grand Prix Race (R). A 2025 Sprint weekend features FP1 and Sprint Qualifying (SQ1: 12 min on new Mediums; "
            "SQ2: 10 min on new Mediums; SQ3: 8 min on Softs) on Friday, the 100 km Sprint (S) and Grand Prix Qualifying "
            "(Q) on Saturday, and the Grand Prix (R) on Sunday."
        ),
    ),
    KnowledgeDocument(
        doc_id="f1_2025_calendar_circuits",
        title="2025 FIA Formula 1 World Championship Official Calendar & Circuits",
        category="2025 Season & Circuits",
        url="https://www.formula1.com/en/racing/2025.html",
        source_org="Formula 1",
        retrieval_date="2025-03-01",
        keywords=("2025", "calendar", "schedule", "circuits", "rounds", "australia", "china", "japan", "bahrain", "monaco", "silverstone", "monza", "spa", "abu dhabi"),
        content=(
            "The 2025 FIA Formula 1 World Championship comprises 24 Grands Prix: R1 Australia (Melbourne), R2 China (Shanghai, Sprint), "
            "R3 Japan (Suzuka), R4 Bahrain (Sakhir), R5 Saudi Arabia (Jeddah), R6 Miami (Sprint), R7 Emilia Romagna (Imola), "
            "R8 Monaco, R9 Spain (Barcelona), R10 Canada (Montreal), R11 Austria (Spielberg), R12 Great Britain (Silverstone), "
            "R13 Belgium (Spa-Francorchamps, Sprint), R14 Hungary (Budapest), R15 Netherlands (Zandvoort), R16 Italy (Monza), "
            "R17 Azerbaijan (Baku), R18 Singapore (Marina Bay), R19 United States (Austin, Sprint), R20 Mexico City, "
            "R21 São Paulo (Interlagos, Sprint), R22 Las Vegas, R23 Qatar (Lusail, Sprint), and R24 Abu Dhabi (Yas Marina)."
        ),
    ),
    KnowledgeDocument(
        doc_id="f1_2025_teams_drivers",
        title="2025 Formula 1 Teams & Driver Lineup Reference",
        category="Teams & Drivers",
        url="https://www.formula1.com/en/drivers.html",
        source_org="Formula 1",
        retrieval_date="2025-03-15",
        keywords=("drivers", "teams", "lineup", "2025", "mclaren", "ferrari", "red bull", "mercedes", "williams", "aston martin", "alpine", "haas", "sauber", "racing bulls", "hamilton", "verstappen", "norris", "leclerc", "piastri"),
        content=(
            "2025 Formula 1 Constructor & Driver Lineups: McLaren (Lando Norris #4, Oscar Piastri #81); Ferrari (Charles Leclerc #16, "
            "Lewis Hamilton #44); Red Bull Racing (Max Verstappen #1, Liam Lawson #30 / Yuki Tsunoda #22); Mercedes (George Russell #63, "
            "Kimi Antonelli #12); Aston Martin (Fernando Alonso #14, Lance Stroll #18); Alpine (Pierre Gasly #10, Jack Doohan #7); "
            "Haas F1 Team (Esteban Ocon #31, Oliver Bearman #87); Racing Bulls (Yuki Tsunoda #22 / Liam Lawson #30, Isack Hadjar #6); "
            "Williams (Alex Albon #23, Carlos Sainz #55); Kick Sauber (Nico Hülkenberg #27, Gabriel Bortoleto #5)."
        ),
    ),
    KnowledgeDocument(
        doc_id="f1_sector_timing_colours",
        title="Formula 1 Official Timing Screen Sector Colours & Telemetry Signals",
        category="Telemetry & Timing",
        url="https://www.formula1.com/en/latest/article/f1-timing-screens-explained",
        source_org="Formula 1",
        retrieval_date="2025-03-01",
        keywords=("sector", "purple", "green", "yellow", "telemetry", "throttle", "brake", "gear", "speed", "ideal lap", "theoretical best"),
        content=(
            "On official Formula 1 timing screens, each lap is divided into three sectors (Sector 1, Sector 2, Sector 3). "
            "A Purple sector indicates the fastest time set by any driver in the session so far (Session Best). A Green "
            "sector indicates a driver's personal fastest time in that sector (Personal Best). A driver's Theoretical Best "
            "(or Ideal Lap) is the sum of their best Sector 1, Sector 2, and Sector 3 times. Car telemetry channels include "
            "Speed (km/h), Throttle (0–100% pedal application), Brake (on/off or pressure percentage), Gear (1–8), and DRS status."
        ),
    ),
]


def _tokenize(text: str) -> List[str]:
    return [t for t in re.findall(r"[a-z0-9]+", (text or "").lower()) if len(t) > 1]


class F1KnowledgeRetriever:
    """
    Lightweight BM25 + keyword-boosted retrieval index over trusted FIA and Formula 1
    reference documents. Requires no external vector database.
    """

    def __init__(self, documents: Optional[List[KnowledgeDocument]] = None) -> None:
        self.documents: List[KnowledgeDocument] = documents or TRUSTED_F1_CORPUS
        self._doc_tokens: List[List[str]] = []
        self._doc_freqs: Dict[str, int] = {}
        self._avg_dl: float = 1.0
        self._build_index()

    def _build_index(self) -> None:
        total_len = 0
        for doc in self.documents:
            full_text = f"{doc.title} {doc.category} {' '.join(doc.keywords)} {doc.content}"
            tokens = _tokenize(full_text)
            self._doc_tokens.append(tokens)
            total_len += len(tokens)
            seen: Set[str] = set(tokens)
            for tok in seen:
                self._doc_freqs[tok] = self._doc_freqs.get(tok, 0) + 1
        self._avg_dl = max(1.0, total_len / max(1, len(self.documents)))

    def retrieve(self, query: str, top_k: int = 3) -> List[KnowledgeDocument]:
        q_tokens = _tokenize(query)
        if not q_tokens:
            return self.documents[:top_k]

        q_lower = (query or "").lower()
        n_docs = len(self.documents)
        k1 = 1.5
        b = 0.75
        scored: List[Tuple[float, int]] = []

        for idx, doc in enumerate(self.documents):
            d_tokens = self._doc_tokens[idx]
            dl = len(d_tokens)
            tf_map: Dict[str, int] = {}
            for t in d_tokens:
                tf_map[t] = tf_map.get(t, 0) + 1

            score = 0.0
            for qt in q_tokens:
                tf = tf_map.get(qt, 0)
                if tf > 0:
                    df = self._doc_freqs.get(qt, 1)
                    idf = math.log(1.0 + (n_docs - df + 0.5) / (df + 0.5))
                    denom = tf + k1 * (1.0 - b + b * (dl / self._avg_dl))
                    score += idf * ((tf * (k1 + 1.0)) / denom)

            for kw in doc.keywords:
                if kw in q_lower:
                    score += 2.5

            if score > 0:
                scored.append((score, idx))

        scored.sort(key=lambda item: item[0], reverse=True)
        if not scored:
            return [self.documents[0], self.documents[1]][:top_k]
        return [self.documents[idx] for _, idx in scored[:top_k]]


retriever = F1KnowledgeRetriever()
