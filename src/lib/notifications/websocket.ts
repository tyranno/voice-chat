/**
 * 알림 WebSocket 연결 관리
 * 서버와 WebSocket으로 연결하여 프로액티브 알림을 수신
 */

export interface NotificationMessage {
	type: 'notification';
	title: string;
	body: string;
	action?: string;
}

export interface NotificationWSCallbacks {
	onNotification: (msg: NotificationMessage) => void;
	onConnected?: () => void;
	onDisconnected?: () => void;
}

export class NotificationWebSocket {
	private ws: WebSocket | null = null;
	private url: string;
	private instanceId: string;
	private callbacks: NotificationWSCallbacks;
	private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
	private pingTimer: ReturnType<typeof setInterval> | null = null;
	private destroyed = false;
	private reconnectDelay = 3000;

	constructor(url: string, instanceId: string, callbacks: NotificationWSCallbacks) {
		this.url = url;
		this.instanceId = instanceId;
		this.callbacks = callbacks;
	}

	/** 연결 시작 */
	connect() {
		if (this.destroyed) return;
		this.cleanup();

		try {
			this.ws = new WebSocket(this.url);
		} catch (e) {
			console.error('[NotifyWS] WebSocket 생성 실패:', e);
			this.scheduleReconnect();
			return;
		}

		this.ws.onopen = () => {
			console.log('[NotifyWS] 연결됨');
			this.reconnectDelay = 3000; // 리셋

			// 등록 메시지 전송
			this.ws?.send(JSON.stringify({ instanceId: this.instanceId }));
			this.callbacks.onConnected?.();

			// ping 하트비트 (60초 간격)
			this.pingTimer = setInterval(() => {
				if (this.ws?.readyState === WebSocket.OPEN) {
					this.ws.send(JSON.stringify({ type: 'ping' }));
				}
			}, 60000);
		};

		this.ws.onmessage = (event) => {
			try {
				const data = JSON.parse(event.data);
				if (data.type === 'notification') {
					this.callbacks.onNotification(data as NotificationMessage);
				}
				// pong은 무시
			} catch (e) {
				console.warn('[NotifyWS] 메시지 파싱 실패:', e);
			}
		};

		this.ws.onclose = () => {
			console.log('[NotifyWS] 연결 끊김');
			this.callbacks.onDisconnected?.();
			this.cleanup();
			this.scheduleReconnect();
		};

		this.ws.onerror = (e) => {
			console.error('[NotifyWS] 에러:', e);
		};
	}

	/** 연결 종료 */
	destroy() {
		this.destroyed = true;
		this.cleanup();
		if (this.ws) {
			this.ws.close();
			this.ws = null;
		}
	}

	private cleanup() {
		if (this.pingTimer) {
			clearInterval(this.pingTimer);
			this.pingTimer = null;
		}
		if (this.reconnectTimer) {
			clearTimeout(this.reconnectTimer);
			this.reconnectTimer = null;
		}
	}

	private scheduleReconnect() {
		if (this.destroyed) return;
		this.reconnectTimer = setTimeout(() => {
			console.log('[NotifyWS] 재연결 시도...');
			this.connect();
		}, this.reconnectDelay);
		// 백오프 (최대 30초)
		this.reconnectDelay = Math.min(this.reconnectDelay * 1.5, 30000);
	}
}
