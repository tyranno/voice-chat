import { Capacitor, registerPlugin } from '@capacitor/core';
import { settings } from '$lib/stores/settings.svelte';

interface AppUpdaterPlugin {
	downloadAndInstall(opts: { url: string }): Promise<{ success: boolean; downloaded?: boolean; size?: number }>;
	installPending(): Promise<{ success: boolean }>;
	addListener(
		event: 'downloadProgress',
		fn: (data: { progress: number; downloaded?: number; total?: number }) => void
	): Promise<{ remove: () => void }>;
}

const AppUpdater = registerPlugin<AppUpdaterPlugin>('AppUpdater');

export interface ApkInfo {
	version: string;
	versionCode: number;
	size: number;
	downloadUrl: string;
	updatedAt?: string;
}

export async function checkForUpdate(): Promise<{ available: boolean; info?: ApkInfo; error?: string }> {
	try {
		const res = await fetch(`${settings.serverUrl}/api/apk/latest`);
		if (!res.ok) return { available: false, error: res.status === 404 ? 'No APK on server' : `Error ${res.status}` };
		const info: ApkInfo = await res.json();
		return { available: true, info };
	} catch (e: any) {
		return { available: false, error: e.message };
	}
}

export async function downloadAndInstall(
	onProgress?: (percent: number) => void
): Promise<{ success: boolean; error?: string }> {
	if (!Capacitor.isNativePlatform()) {
		return { success: false, error: 'Only available on Android' };
	}

	try {
		const url = `${settings.serverUrl}/api/apk/download`;

		let listenerHandle: { remove: () => void } | null = null;
		if (onProgress) {
			listenerHandle = await AppUpdater.addListener('downloadProgress', (data) => {
				const p = data?.progress;
				if (typeof p === 'number' && Number.isFinite(p) && p >= 0) {
					onProgress(p);
				}
			});
		}

		const result = await AppUpdater.downloadAndInstall({ url });

		if (listenerHandle) listenerHandle.remove();
		return { success: !!result?.success };
	} catch (e: any) {
		return { success: false, error: e.message };
	}
}

export async function triggerInstall(): Promise<{ success: boolean; error?: string }> {
	if (!Capacitor.isNativePlatform()) return { success: false, error: 'Only available on Android' };
	try {
		const r = await AppUpdater.installPending();
		return { success: !!r?.success };
	} catch (e: any) {
		return { success: false, error: e.message };
	}
}
