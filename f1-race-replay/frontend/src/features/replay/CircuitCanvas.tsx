import React, { useEffect, useRef, useState } from 'react';
import { DriverInfo, ReplayFrame, TrackGeometry } from '../../types/f1';
import { Compass, Disc, Eye, EyeOff, Layers, ShieldAlert } from 'lucide-react';

interface CircuitCanvasProps {
  trackGeometry: TrackGeometry;
  frame: ReplayFrame | null;
  drivers: DriverInfo[];
  selectedDriver: string | null;
  compareDriver: string | null;
  onSelectDriver: (code: string) => void;
}

export const CircuitCanvas: React.FC<CircuitCanvasProps> = ({
  trackGeometry,
  frame,
  drivers,
  selectedDriver,
  compareDriver,
  onSelectDriver,
}) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [viewMode, setViewMode] = useState<'circuit' | 'circular'>('circuit');
  const [showDrsZones, setShowDrsZones] = useState(true);
  const [showDriverLabels, setShowDriverLabels] = useState(true);
  const [canvasSize, setCanvasSize] = useState({ width: 800, height: 520 });

  const driverColorMap = React.useMemo(() => {
    const map: Record<string, string> = {};
    for (const d of drivers) {
      map[d.code] = d.color || '#38bdf8';
    }
    return map;
  }, [drivers]);

  useEffect(() => {
    if (!containerRef.current) return;
    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width, height } = entry.contentRect;
        if (width > 100 && height > 100) {
          setCanvasSize({ width: Math.floor(width), height: Math.floor(height) });
        }
      }
    });
    observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !trackGeometry) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    canvas.width = canvasSize.width * dpr;
    canvas.height = canvasSize.height * dpr;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    const w = canvasSize.width;
    const h = canvasSize.height;

    // Clear background with subtle grid
    ctx.fillStyle = '#0B0E14';
    ctx.fillRect(0, 0, w, h);

    ctx.strokeStyle = 'rgba(38, 48, 70, 0.35)';
    ctx.lineWidth = 1;
    const gridStep = 40;
    for (let gx = 0; gx < w; gx += gridStep) {
      ctx.beginPath();
      ctx.moveTo(gx, 0);
      ctx.lineTo(gx, h);
      ctx.stroke();
    }
    for (let gy = 0; gy < h; gy += gridStep) {
      ctx.beginPath();
      ctx.moveTo(0, gy);
      ctx.lineTo(w, gy);
      ctx.stroke();
    }

    if (viewMode === 'circular') {
      // Circular Track Position Schematic (migrated from src/insights/driver_track_positions.py)
      const cx = w / 2;
      const cy = h / 2;
      const radius = Math.min(w, h) * 0.36;

      ctx.beginPath();
      ctx.arc(cx, cy, radius, 0, Math.PI * 2);
      ctx.strokeStyle = '#1e293b';
      ctx.lineWidth = 22;
      ctx.stroke();

      ctx.beginPath();
      ctx.arc(cx, cy, radius, 0, Math.PI * 2);
      ctx.strokeStyle = '#475569';
      ctx.lineWidth = 2;
      ctx.stroke();

      ctx.strokeStyle = '#f8fafc';
      ctx.lineWidth = 3;
      ctx.beginPath();
      ctx.moveTo(cx, cy - radius - 14);
      ctx.lineTo(cx, cy - radius + 14);
      ctx.stroke();
      ctx.fillStyle = '#94a3b8';
      ctx.font = '600 11px Inter, sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText('S/F (0%)', cx, cy - radius - 20);

      if (frame?.drivers) {
        const entries = Object.entries(frame.drivers).sort(
          (a, b) => (b[1].position || 99) - (a[1].position || 99)
        );
        for (const [code, state] of entries) {
          const rel = ((state.rel_dist % 1) + 1) % 1;
          const angle = -Math.PI / 2 + rel * Math.PI * 2;
          const dx = cx + Math.cos(angle) * radius;
          const dy = cy + Math.sin(angle) * radius;
          const color = driverColorMap[code] || '#38bdf8';
          const isSelected = code === selectedDriver || code === compareDriver;

          if (isSelected) {
            ctx.beginPath();
            ctx.arc(dx, dy, 13, 0, Math.PI * 2);
            ctx.strokeStyle = '#ffffff';
            ctx.lineWidth = 2;
            ctx.stroke();
          }

          ctx.beginPath();
          ctx.arc(dx, dy, isSelected ? 8 : 6, 0, Math.PI * 2);
          ctx.fillStyle = color;
          ctx.fill();
          ctx.strokeStyle = '#0B0E14';
          ctx.lineWidth = 1.5;
          ctx.stroke();

          if (showDriverLabels) {
            const labelRadius = radius + (state.position % 2 === 0 ? 26 : -26);
            const lx = cx + Math.cos(angle) * labelRadius;
            const ly = cy + Math.sin(angle) * labelRadius;
            ctx.fillStyle = isSelected ? '#ffffff' : '#e2e8f0';
            ctx.font = `${isSelected ? '700' : '600'} 11px JetBrains Mono, monospace`;
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillText(code, lx, ly);
          }
        }
      }
      return;
    }

    // Real Circuit Geometry mode (reusing TrackGeometry coordinates from src/f1_data.py)
    const { x_ref, y_ref, x_inner, y_inner, x_outer, y_outer, x_min, x_max, y_min, y_max, drs_zones } =
      trackGeometry;
    const worldW = Math.max(1, x_max - x_min);
    const worldH = Math.max(1, y_max - y_min);
    const pad = 48;
    const scale = Math.min((w - pad * 2) / worldW, (h - pad * 2) / worldH);
    const offsetX = (w - worldW * scale) / 2 - x_min * scale;
    const offsetY = (h - worldH * scale) / 2 - y_min * scale;

    const toScreen = (wx: number, wy: number): [number, number] => [
      wx * scale + offsetX,
      h - (wy * scale + offsetY),
    ];

    // 1. Draw track asphalt ribbon along x_ref/y_ref
    if (x_ref && x_ref.length > 2) {
      ctx.beginPath();
      const [sx0, sy0] = toScreen(x_ref[0], y_ref[0]);
      ctx.moveTo(sx0, sy0);
      for (let i = 1; i < x_ref.length; i++) {
        const [sx, sy] = toScreen(x_ref[i], y_ref[i]);
        ctx.lineTo(sx, sy);
      }
      ctx.closePath();
      ctx.strokeStyle = '#1E2638';
      ctx.lineWidth = 14;
      ctx.lineJoin = 'round';
      ctx.lineCap = 'round';
      ctx.stroke();
    }

    // 2. Draw inner and outer track edge boundaries
    const drawBoundary = (xs: number[], ys: number[]) => {
      if (!xs || xs.length < 2) return;
      ctx.beginPath();
      const [bx0, by0] = toScreen(xs[0], ys[0]);
      ctx.moveTo(bx0, by0);
      for (let i = 1; i < xs.length; i++) {
        const [bx, by] = toScreen(xs[i], ys[i]);
        ctx.lineTo(bx, by);
      }
      ctx.closePath();
      ctx.strokeStyle = '#64748b';
      ctx.lineWidth = 1.6;
      ctx.stroke();
    };
    drawBoundary(x_inner, y_inner);
    drawBoundary(x_outer, y_outer);

    // 3. Draw DRS Zones in vibrant emerald green along outer track boundary
    if (showDrsZones && drs_zones?.length && x_outer?.length) {
      for (const zone of drs_zones) {
        const sIdx = Math.max(0, zone.start?.index ?? 0);
        const eIdx = Math.min(x_outer.length - 1, zone.end?.index ?? 0);
        if (eIdx <= sIdx) continue;
        ctx.beginPath();
        const [dx0, dy0] = toScreen(x_outer[sIdx], y_outer[sIdx]);
        ctx.moveTo(dx0, dy0);
        for (let i = sIdx + 1; i <= eIdx; i++) {
          const [dx, dy] = toScreen(x_outer[i], y_outer[i]);
          ctx.lineTo(dx, dy);
        }
        ctx.strokeStyle = '#00D26A';
        ctx.lineWidth = 4;
        ctx.stroke();
      }
    }

    // 4. Draw Start / Finish Checkered Line at index 0
    if (x_inner?.length && x_outer?.length) {
      const [ix, iy] = toScreen(x_inner[0], y_inner[0]);
      const [ox, oy] = toScreen(x_outer[0], y_outer[0]);
      ctx.beginPath();
      ctx.moveTo(ix, iy);
      ctx.lineTo(ox, oy);
      ctx.strokeStyle = '#ffffff';
      ctx.lineWidth = 4;
      ctx.stroke();

      ctx.beginPath();
      ctx.moveTo(ix, iy);
      ctx.lineTo(ox, oy);
      ctx.strokeStyle = '#E10600';
      ctx.setLineDash([3, 3]);
      ctx.lineWidth = 4;
      ctx.stroke();
      ctx.setLineDash([]);
    }

    // 5. Draw Simulated Safety Car if active
    if (frame?.safety_car && frame.safety_car.alpha > 0.05) {
      const sc = frame.safety_car;
      const [scX, scY] = toScreen(sc.x, sc.y);
      ctx.save();
      ctx.globalAlpha = Math.min(1, sc.alpha);

      ctx.beginPath();
      ctx.arc(scX, scY, 13, 0, Math.PI * 2);
      ctx.fillStyle = 'rgba(245, 158, 11, 0.28)';
      ctx.fill();
      ctx.strokeStyle = '#f59e0b';
      ctx.lineWidth = 2;
      ctx.stroke();

      ctx.beginPath();
      ctx.arc(scX, scY, 6.5, 0, Math.PI * 2);
      ctx.fillStyle = '#f59e0b';
      ctx.fill();

      ctx.fillStyle = '#fef3c7';
      ctx.font = '700 10px JetBrains Mono, monospace';
      ctx.textAlign = 'left';
      ctx.fillText('SC (SIMULATED)', scX + 14, scY + 3);
      ctx.restore();
    }

    // 6. Draw Drivers (backmarkers first so P1 renders on top)
    if (frame?.drivers) {
      const sortedDrivers = Object.entries(frame.drivers).sort(
        (a, b) => (b[1].position || 99) - (a[1].position || 99)
      );

      for (const [code, state] of sortedDrivers) {
        const [dx, dy] = toScreen(state.x, state.y);
        const color = driverColorMap[code] || '#38bdf8';
        const isPrimary = code === selectedDriver;
        const isCompare = code === compareDriver;
        const isHighlighted = isPrimary || isCompare;
        const isOut = state.status === 'OUT' || state.status === 'DNF';

        ctx.save();
        if (isOut) {
          ctx.globalAlpha = 0.35;
        }

        if (isHighlighted) {
          ctx.beginPath();
          ctx.arc(dx, dy, 12, 0, Math.PI * 2);
          ctx.strokeStyle = isPrimary ? '#ffffff' : '#38bdf8';
          ctx.lineWidth = 2.2;
          ctx.stroke();
        }

        ctx.beginPath();
        ctx.arc(dx, dy, isHighlighted ? 7 : 5.5, 0, Math.PI * 2);
        ctx.fillStyle = color;
        ctx.fill();
        ctx.strokeStyle = '#0B0E14';
        ctx.lineWidth = 1.5;
        ctx.stroke();

        if (showDriverLabels || isHighlighted) {
          const offsetY = state.position % 2 === 0 ? -13 : 14;
          const labelX = dx + 9;
          const labelY = dy + offsetY * 0.6;

          ctx.font = `${isHighlighted ? '700' : '600'} 10px JetBrains Mono, monospace`;
          const textWidth = ctx.measureText(code).width;
          ctx.fillStyle = isHighlighted ? 'rgba(15, 23, 42, 0.92)' : 'rgba(11, 14, 20, 0.78)';
          ctx.fillRect(labelX - 3, labelY - 8, textWidth + 6, 13);

          ctx.fillStyle = isHighlighted ? '#ffffff' : color;
          ctx.textAlign = 'left';
          ctx.textBaseline = 'middle';
          ctx.fillText(code, labelX, labelY - 1);
        }

        ctx.restore();
      }
    }
  }, [
    trackGeometry,
    frame,
    canvasSize,
    viewMode,
    showDrsZones,
    showDriverLabels,
    selectedDriver,
    compareDriver,
    driverColorMap,
  ]);

  const handleCanvasClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!frame?.drivers || !trackGeometry || viewMode !== 'circuit') return;
    const rect = e.currentTarget.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const clickY = e.clientY - rect.top;

    const { x_min, x_max, y_min, y_max } = trackGeometry;
    const worldW = Math.max(1, x_max - x_min);
    const worldH = Math.max(1, y_max - y_min);
    const pad = 48;
    const scale = Math.min(
      (canvasSize.width - pad * 2) / worldW,
      (canvasSize.height - pad * 2) / worldH
    );
    const offsetX = (canvasSize.width - worldW * scale) / 2 - x_min * scale;
    const offsetY = (canvasSize.height - worldH * scale) / 2 - y_min * scale;

    let closestCode: string | null = null;
    let closestDist = 20;

    for (const [code, state] of Object.entries(frame.drivers)) {
      const sx = state.x * scale + offsetX;
      const sy = canvasSize.height - (state.y * scale + offsetY);
      const dist = Math.hypot(clickX - sx, clickY - sy);
      if (dist < closestDist) {
        closestDist = dist;
        closestCode = code;
      }
    }
    if (closestCode) {
      onSelectDriver(closestCode);
    }
  };

  const trackStatusCode = frame?.track_status || '1';
  const trackStatusLabel = frame?.track_status_label || 'GREEN FLAG';

  const statusBadgeStyle =
    trackStatusCode === '4' || trackStatusCode === '6' || trackStatusCode === '7'
      ? 'bg-amber-500/20 text-amber-300 border-amber-500/50'
      : trackStatusCode === '5'
      ? 'bg-red-500/20 text-red-300 border-red-500/50'
      : trackStatusCode === '2'
      ? 'bg-yellow-500/20 text-yellow-300 border-yellow-500/50'
      : 'bg-emerald-500/15 text-emerald-300 border-emerald-500/40';

  return (
    <div
      ref={containerRef}
      className="relative w-full h-full min-h-[420px] bg-[#0B0E14] rounded-xl border border-[#263046] overflow-hidden flex flex-col"
    >
      {/* Top Overlay HUD Bar */}
      <div className="absolute top-3 left-3 right-3 z-10 flex flex-wrap items-center justify-between gap-2 pointer-events-none">
        <div className="flex items-center gap-2 pointer-events-auto">
          <span
            className={`px-2.5 py-1 rounded-md text-xs font-mono font-bold border ${statusBadgeStyle}`}
          >
            {trackStatusLabel}
          </span>
          {frame?.safety_car && frame.safety_car.alpha > 0.05 && (
            <span
              className="flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-mono font-semibold bg-amber-500/20 text-amber-200 border border-amber-400/50"
              title="Safety Car coordinates are mathematically approximated ahead of the race leader from FIA TrackStatus timestamps"
            >
              <ShieldAlert className="w-3.5 h-3.5 text-amber-400" />
              SC POSITION APPROXIMATED ({(frame.safety_car.phase || 'DEPLOYED').toUpperCase()})
            </span>
          )}
        </div>

        {/* Canvas View Controls */}
        <div className="flex items-center gap-1.5 bg-[#121722]/90 backdrop-blur-md px-2 py-1 rounded-lg border border-[#263046] pointer-events-auto">
          <button
            type="button"
            onClick={() => setViewMode(viewMode === 'circuit' ? 'circular' : 'circuit')}
            className="flex items-center gap-1 px-2 py-1 rounded text-xs font-medium text-slate-200 hover:bg-[#192030] transition"
            title="Switch between Real Circuit Geometry and Circular Track Position Ring"
          >
            {viewMode === 'circuit' ? (
              <>
                <Disc className="w-3.5 h-3.5 text-sky-400" />
                <span>Circular Ring</span>
              </>
            ) : (
              <>
                <Compass className="w-3.5 h-3.5 text-emerald-400" />
                <span>Real Circuit</span>
              </>
            )}
          </button>

          <button
            type="button"
            onClick={() => setShowDrsZones(!showDrsZones)}
            className={`flex items-center gap-1 px-2 py-1 rounded text-xs font-medium transition ${
              showDrsZones ? 'text-emerald-400 bg-emerald-500/10' : 'text-slate-400 hover:bg-[#192030]'
            }`}
            title="Toggle DRS Zone highlights"
          >
            <Layers className="w-3.5 h-3.5" />
            <span>DRS</span>
          </button>

          <button
            type="button"
            onClick={() => setShowDriverLabels(!showDriverLabels)}
            className={`flex items-center gap-1 px-2 py-1 rounded text-xs font-medium transition ${
              showDriverLabels ? 'text-sky-400 bg-sky-500/10' : 'text-slate-400 hover:bg-[#192030]'
            }`}
            title="Toggle 3-letter driver labels"
          >
            {showDriverLabels ? <Eye className="w-3.5 h-3.5" /> : <EyeOff className="w-3.5 h-3.5" />}
            <span>Labels</span>
          </button>
        </div>
      </div>

      {/* Main Interactive HTML5 Canvas */}
      <canvas
        ref={canvasRef}
        onClick={handleCanvasClick}
        className="w-full h-full cursor-pointer block"
      />

      {/* Bottom Legend & Track Info */}
      <div className="absolute bottom-2.5 left-3 right-3 flex flex-wrap items-center justify-between text-[11px] text-slate-400 font-mono pointer-events-none">
        <div className="flex items-center gap-3 bg-[#121722]/85 px-2.5 py-1 rounded border border-[#263046]">
          <span>CIRCUIT: {Math.round(trackGeometry.circuit_length_m || 5300)}m</span>
          <span className="text-emerald-400">● DRS ZONE</span>
          <span className="text-amber-400">● SC (APPROXIMATED)</span>
        </div>
        <div className="bg-[#121722]/85 px-2.5 py-1 rounded border border-[#263046]">
          Click any car marker to inspect driver telemetry
        </div>
      </div>
    </div>
  );
};
