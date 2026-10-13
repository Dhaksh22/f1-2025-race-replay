import { LeaderboardSnapshot, ReplayFrame } from '../types/f1';

export interface ReplayStreamPacket {
  type: 'frame';
  frame_index: number;
  total_frames: number;
  is_paused: boolean;
  playback_speed: number;
  frame: ReplayFrame | null;
  leaderboard?: LeaderboardSnapshot;
}

export type StreamConnectionMode = 'websocket' | 'local-interpolated' | 'reconnecting';

interface ReplayStreamCallbacks {
  onFramePacket: (packet: ReplayStreamPacket) => void;
  onConnectionChange: (mode: StreamConnectionMode) => void;
}

export class ReplayStreamClient {
  private ws: WebSocket | null = null;
  private roundNumber: number;
  private sessionType: string;
  private callbacks: ReplayStreamCallbacks;
  private closedExplicitly = false;
  private reconnectTimer: number | null = null;

  constructor(roundNumber: number, sessionType: string, callbacks: ReplayStreamCallbacks) {
    this.roundNumber = roundNumber;
    this.sessionType = sessionType;
    this.callbacks = callbacks;
  }

  public connect(): void {
    this.closedExplicitly = false;
    const configuredWsBase = import.meta.env.VITE_WS_BASE_URL;
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsBase = configuredWsBase
      ? configuredWsBase.replace(/\/$/, '')
      : `${protocol}//${window.location.host}/api/ws`;

    const wsUrl = `${wsBase}/replay/2025/${this.roundNumber}?session_type=${encodeURIComponent(
      this.sessionType
    )}`;

    try {
      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        this.callbacks.onConnectionChange('websocket');
      };

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'session_init' && data.initial_frame) {
            this.callbacks.onFramePacket(data.initial_frame as ReplayStreamPacket);
          } else if (data.type === 'frame') {
            this.callbacks.onFramePacket(data as ReplayStreamPacket);
          }
        } catch {
          // ignore malformed packet
        }
      };

      this.ws.onerror = () => {
        this.callbacks.onConnectionChange('local-interpolated');
      };

      this.ws.onclose = () => {
        if (!this.closedExplicitly) {
          this.callbacks.onConnectionChange('local-interpolated');
        }
      };
    } catch {
      this.callbacks.onConnectionChange('local-interpolated');
    }
  }

  public sendCommand(payload: Record<string, unknown>): boolean {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(payload));
      return true;
    }
    return false;
  }

  public disconnect(): void {
    this.closedExplicitly = true;
    if (this.reconnectTimer !== null) {
      window.clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    if (this.ws) {
      try {
        this.ws.close();
      } catch {
        // ignore close error
      }
      this.ws = null;
    }
  }
}
