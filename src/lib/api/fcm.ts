/**
 * FCM token management — registers device token with GCP server
 */
import { Capacitor, registerPlugin } from '@capacitor/core';
import { settings } from '$lib/stores/settings.svelte';

interface FcmPluginInterface {
	getToken(): Promise<{ token: string }>;
}

const FcmPlugin = registerPlugin<FcmPluginInterface>('FcmPlugin');

export async function registerFcmToken(): Promise<string | null> {
	if (Capacitor.getPlatform() !== 'android') return null;

	try {
		const { token } = await FcmPlugin.getToken();
		console.log('[FCM] Token:', token);

		// Send token to server
		await fetch(`${settings.serverUrl}/api/fcm/register`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({
				token,
				instanceId: settings.selectedInstance
			})
		});
		console.log('[FCM] Token registered with server');
		return token;
	} catch (e) {
		console.error('[FCM] Registration failed:', e);
		return null;
	}
}
