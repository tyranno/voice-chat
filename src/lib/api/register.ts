/**
 * Device registration — register app with server using access code
 */
import { settings } from '$lib/stores/settings.svelte';

export interface RegisterResult {
	id: string;
	name: string;
	token: string;
}

export async function registerDevice(accessCode: string, deviceName: string): Promise<RegisterResult> {
	const res = await fetch(`${settings.serverUrl}/api/register`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ accessCode, deviceName }),
		signal: AbortSignal.timeout(10000)
	});

	if (!res.ok) {
		const text = await res.text().catch(() => '');
		if (res.status === 403) throw new Error('잘못된 등록 코드입니다');
		throw new Error(`등록 실패: ${text || res.status}`);
	}

	return await res.json();
}
