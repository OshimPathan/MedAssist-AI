/**
 * MedAssist AI - WebSocket Service
 * Handles real-time bidirectional communication with the backend
 */

type MessageHandler = (data: any) => void;

class WebSocketService {
    private ws: WebSocket | null = null;
    private sessionId: string;
    private handlers: Map<string, MessageHandler[]> = new Map();
    private reconnectAttempts = 0;
    private maxReconnectAttempts = 5;
    private reconnectDelay = 1000;

    constructor() {
        this.sessionId = this.generateSessionId();
    }

    private generateSessionId(): string {
        return 'session_' + Date.now() + '_' + Math.random().toString(36).substring(2, 9);
    }

    getSessionId(): string {
        return this.sessionId;
    }

    connect(): Promise<void> {
        return new Promise((resolve, reject) => {
            const wsUrl = `ws://localhost:8000/api/chat/ws/${this.sessionId}`;

            try {
                this.ws = new WebSocket(wsUrl);

                this.ws.onopen = () => {
                    console.log('WebSocket connected');
                    this.reconnectAttempts = 0;
                    this.emit('connected', { sessionId: this.sessionId });
                    resolve();
                };

                this.ws.onmessage = (event) => {
                    try {
                        const data = JSON.parse(event.data);
                        this.emit('message', data);
                    } catch {
                        console.error('Failed to parse message:', event.data);
                    }
                };

                this.ws.onclose = (event) => {
                    console.log('WebSocket closed:', event.code, event.reason);
                    this.emit('disconnected', { code: event.code });
                    this.attemptReconnect();
                };

                this.ws.onerror = (error) => {
                    console.error('WebSocket error:', error);
                    this.emit('error', { error });
                    reject(error);
                };
            } catch (error) {
                reject(error);
            }
        });
    }

    private attemptReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            const delay = this.reconnectDelay * this.reconnectAttempts;
            console.log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`);
            setTimeout(() => this.connect().catch(() => { }), delay);
        }
    }

    sendMessage(message: string, metadata?: Record<string, string>) {
        if (this.ws?.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({
                message,
                ...metadata,
            }));
        } else {
            console.error('WebSocket not connected');
            this.emit('error', { error: 'Not connected' });
        }
    }

    on(event: string, handler: MessageHandler) {
        if (!this.handlers.has(event)) {
            this.handlers.set(event, []);
        }
        this.handlers.get(event)!.push(handler);
    }

    off(event: string, handler: MessageHandler) {
        const handlers = this.handlers.get(event);
        if (handlers) {
            this.handlers.set(event, handlers.filter(h => h !== handler));
        }
    }

    private emit(event: string, data: any) {
        const handlers = this.handlers.get(event);
        if (handlers) {
            handlers.forEach(h => h(data));
        }
    }

    disconnect() {
        this.maxReconnectAttempts = 0;
        this.ws?.close();
        this.ws = null;
    }

    isConnected(): boolean {
        return this.ws?.readyState === WebSocket.OPEN;
    }
}

// Fallback REST-based message sending for when WebSocket is unavailable
export async function sendMessageREST(
    message: string,
    sessionId?: string,
    patientName?: string,
    patientPhone?: string,
): Promise<any> {
    const response = await fetch('http://localhost:8000/api/chat/message', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            message,
            session_id: sessionId,
            patient_name: patientName,
            patient_phone: patientPhone,
        }),
    });
    if (!response.ok) throw new Error('Failed to send message');
    return response.json();
}

export default WebSocketService;
