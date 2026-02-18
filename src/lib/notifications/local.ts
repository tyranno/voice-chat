/**
 * Capacitor Local Notifications 래퍼
 * 백그라운드 상태에서 Android 로컬 알림 표시
 */

import { Capacitor } from '@capacitor/core';

let LocalNotifications: any = null;

/** 플러그인 초기화 (lazy import) */
async function getPlugin() {
	if (LocalNotifications) return LocalNotifications;
	if (!Capacitor.isNativePlatform()) return null;

	try {
		const mod = await import('@capacitor/local-notifications');
		LocalNotifications = mod.LocalNotifications;

		// 권한 요청
		const perm = await LocalNotifications.checkPermissions();
		if (perm.display !== 'granted') {
			await LocalNotifications.requestPermissions();
		}

		return LocalNotifications;
	} catch (e) {
		console.warn('[LocalNotify] 플러그인 로드 실패:', e);
		return null;
	}
}

let notifId = 1;

/** 로컬 알림 표시 */
export async function showLocalNotification(title: string, body: string): Promise<void> {
	const plugin = await getPlugin();
	if (!plugin) return;

	try {
		await plugin.schedule({
			notifications: [
				{
					id: notifId++,
					title,
					body,
					sound: undefined,
					smallIcon: 'ic_stat_notification',
					largeIcon: 'ic_launcher',
				}
			]
		});
	} catch (e) {
		console.error('[LocalNotify] 알림 표시 실패:', e);
	}
}

/** 알림 리스너 등록 (탭 시 콜백) */
export async function onNotificationTap(callback: (data: any) => void): Promise<void> {
	const plugin = await getPlugin();
	if (!plugin) return;

	await plugin.addListener('localNotificationActionPerformed', (event: any) => {
		callback(event.notification?.extra || {});
	});
}
