/**
 * FCM 알림 히스토리 store
 * localStorage에 저장/로드 (최대 100개)
 */
import type { Notification } from '$lib/api/notifications';

const MAX_NOTIFICATIONS = 100;
const STORAGE_KEY = 'vc_notifications';

let notifications = $state<Notification[]>([]);

function load() {
	try {
		const data = localStorage.getItem(STORAGE_KEY);
		if (data) notifications = JSON.parse(data);
	} catch {}
}

function save() {
	try {
		localStorage.setItem(STORAGE_KEY, JSON.stringify(notifications));
	} catch {}
}

// 초기 로드
if (typeof window !== 'undefined') {
	load();
}

export function addNotification(notif: Notification) {
	notifications.unshift(notif);
	if (notifications.length > MAX_NOTIFICATIONS) {
		notifications = notifications.slice(0, MAX_NOTIFICATIONS);
	}
	save();
}

export function clearAll() {
	notifications = [];
	save();
}

export function getNotifications(): Notification[] {
	return notifications;
}
