/**
 * Instance management — list connected OpenClaw bridges
 */
import { settings } from '$lib/stores/settings.svelte';

export interface Instance {
	id: string;
	name: string;
	status: string;
	connectedAt: string;
}

export async function getInstances(): Promise<Instance[]> {
	const res = await fetch(settings.instancesEndpoint, {
		signal: AbortSignal.timeout(5000)
	});

	if (!res.ok) {
		throw new Error(`HTTP ${res.status}`);
	}

	return await res.json();
}
