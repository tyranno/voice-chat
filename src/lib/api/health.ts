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

export async function checkServerHealth(): Promise<HealthResult> {
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
		return { ok: false, latencyMs, error: `HTTP ${res.status}` };
	} catch (err) {
		return {
			ok: false,
			latencyMs: Date.now() - start,
			error: err instanceof Error ? err.message : '연결 실패'
		};
	}
}
