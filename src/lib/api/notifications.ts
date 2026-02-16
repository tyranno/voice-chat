/**
 * FCM notification listener
 * Receives push notifications forwarded from VoiceChatFcmService via Capacitor events
 */
import { Capacitor } from '@capacitor/core';

export interface Notification {
	id: string;
	type: 'info' | 'success' | 'warning' | 'error';
	title: string;
	message: string;
	timestamp: number;
}

type NotificationHandler = (notification: Notification) => void;

const handlers: NotificationHandler[] = [];

/**
 * Register a handler for FCM notifications.
 * On Android, listens for 'fcmNotification' events from the native layer.
 */
export function onFcmNotification(handler: NotificationHandler): () => void {
	handlers.push(handler);
	return () => {
		const idx = handlers.indexOf(handler);
		if (idx >= 0) handlers.splice(idx, 1);
	};
}

// Dispatch to all registered handlers
function dispatch(notif: Notification) {
	handlers.forEach(h => h(notif));
}

// Listen for events from native FCM service
if (typeof window !== 'undefined') {
	window.addEventListener('fcmNotification', (e: any) => {
		const detail = e.detail || {};
		dispatch({
			id: detail.id || String(Date.now()),
			type: detail.type || 'info',
			title: detail.title || '',
			message: detail.message || '',
			timestamp: detail.timestamp || Date.now()
		});
	});
}
