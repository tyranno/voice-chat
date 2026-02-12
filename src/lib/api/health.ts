/**
 * Server health check — ping Gateway to verify connectivity
 */
import { settings } from '$lib/stores/settings.svelte';

export async function checkServerHealth(): Promise<{ ok: boolean; latencyMs: number; error?: string }> {
	const start = Date.now();
	try {
		const headers: Record<string, string> = {};
		if (settings.gatewayToken) {
			headers['Authorization'] = `Bearer ${settings.gatewayToken}`;
		}

		const res = await fetch(`${settings.gatewayUrl}/v1/models`, {
			headers,
			signal: AbortSignal.timeout(5000)
		});

		const latencyMs = Date.now() - start;

		if (res.ok) {
			return { ok: true, latencyMs };
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
