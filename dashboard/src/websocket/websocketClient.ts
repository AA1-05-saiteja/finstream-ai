/**
 * FinStream AI - Robust WebSocket Client
 * Provides automatic reconnection with exponential backoff, keepalive pings, and event dispatching.
 */

import {
  ConnectionStateChangeHandler,
  WebSocketConnectionState,
  WebSocketEvent,
  WebSocketEventHandler,
} from './websocketTypes';

const DEFAULT_WS_URL =
  import.meta.env.VITE_WS_URL || 'ws://localhost:8000/api/v1/ws/transactions';

export class FinStreamWebSocketClient {
  private url: string;
  private ws: WebSocket | null = null;
  private state: WebSocketConnectionState = 'DISCONNECTED';
  private eventListeners: Set<WebSocketEventHandler> = new Set();
  private stateListeners: Set<ConnectionStateChangeHandler> = new Set();

  private reconnectAttempts = 0;
  private maxReconnectAttempts = 20;
  private reconnectTimer: number | null = null;
  private pingTimer: number | null = null;
  private isIntentionallyClosed = false;

  constructor(url: string = DEFAULT_WS_URL) {
    this.url = url;
  }

  public getState(): WebSocketConnectionState {
    return this.state;
  }

  public subscribe(handler: WebSocketEventHandler): () => void {
    this.eventListeners.add(handler);
    return () => this.eventListeners.delete(handler);
  }

  public onStateChange(handler: ConnectionStateChangeHandler): () => void {
    this.stateListeners.add(handler);
    handler(this.state);
    return () => this.stateListeners.delete(handler);
  }

  public connect(): void {
    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
      return;
    }

    this.isIntentionallyClosed = false;
    this.updateState(this.reconnectAttempts > 0 ? 'RECONNECTING' : 'CONNECTING');

    try {
      this.ws = new WebSocket(this.url);

      this.ws.onopen = () => {
        this.reconnectAttempts = 0;
        this.updateState('CONNECTED');
        this.startPingInterval();
      };

      this.ws.onmessage = (event: MessageEvent) => {
        if (event.data === 'pong') {
          return;
        }

        try {
          const parsed = JSON.parse(event.data) as WebSocketEvent;
          this.dispatchEvent(parsed);
        } catch (err) {
          console.warn('[WebSocket] Received malformed message:', event.data, err);
        }
      };

      this.ws.onerror = (err) => {
        console.warn('[WebSocket] Connection error:', err);
        this.updateState('ERROR');
      };

      this.ws.onclose = () => {
        this.stopPingInterval();
        this.ws = null;

        if (!this.isIntentionallyClosed) {
          this.updateState('DISCONNECTED');
          this.scheduleReconnect();
        } else {
          this.updateState('DISCONNECTED');
        }
      };
    } catch (err) {
      console.warn('[WebSocket] Failed to instantiate socket:', err);
      this.updateState('ERROR');
      this.scheduleReconnect();
    }
  }

  public disconnect(): void {
    this.isIntentionallyClosed = true;
    this.clearReconnectTimer();
    this.stopPingInterval();

    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.updateState('DISCONNECTED');
  }

  private updateState(newState: WebSocketConnectionState): void {
    this.state = newState;
    this.stateListeners.forEach((fn) => fn(newState));
  }

  private dispatchEvent(event: WebSocketEvent): void {
    this.eventListeners.forEach((fn) => fn(event));
  }

  private scheduleReconnect(): void {
    if (this.isIntentionallyClosed || this.reconnectTimer !== null) {
      return;
    }

    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.warn('[WebSocket] Maximum reconnection attempts reached.');
      return;
    }

    // Exponential backoff: 1s, 2s, 4s, 8s, max 10s
    const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 10000);
    this.reconnectAttempts++;

    this.updateState('RECONNECTING');
    this.reconnectTimer = window.setTimeout(() => {
      this.reconnectTimer = null;
      this.connect();
    }, delay);
  }

  private clearReconnectTimer(): void {
    if (this.reconnectTimer !== null) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
  }

  private startPingInterval(): void {
    this.stopPingInterval();
    this.pingTimer = window.setInterval(() => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.ws.send('ping');
      }
    }, 15000);
  }

  private stopPingInterval(): void {
    if (this.pingTimer !== null) {
      clearInterval(this.pingTimer);
      this.pingTimer = null;
    }
  }
}

// Singleton WebSocket Client instance
export const wsClient = new FinStreamWebSocketClient();
