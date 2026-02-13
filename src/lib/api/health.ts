/**
 * Server health check — ping VoiceChat server
 */
import { settings } from '$lib/stores/settings.svelte';

export interface HealthResult {
	ok: boolean;
	latencyMs: number;
	instances?: number;
	error?: string;
}

export async function checkServerHealth(retries = 2): Promise<HealthResult> {
	for (let attempt = 0; attempt <= retries; attempt++) {
		const start = Date.now();
		try {
			const res = await fetch(settings.healthEndpoint, {
				signal: AbortSignal.timeout(5000)
			});

			const latencyMs = Date.now() - start;

			if (res.ok) {
				const data = await res.json();
				return { ok: true, latencyMs, instances: data.instances ?? 0 };
			}
			if (attempt < retries) {
				await new Promise(r => setTimeout(r, 1000 * (attempt + 1)));
				continue;
			}
			return { ok: false, latencyMs, error: `HTTP ${res.status}` };
		} catch (err) {
			if (attempt < retries) {
				await new Promise(r => setTimeout(r, 1000 * (attempt + 1)));
				continue;
			}
			return {
				ok: false,
				latencyMs: Date.now() - start,
				error: err instanceof Error ? err.message : '연결 실패'
			};
		}
	}
	return { ok: false, latencyMs: 0, error: '연결 실패' };
}
