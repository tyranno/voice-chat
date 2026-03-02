/**
 * YouTube stream URL resolver (server fallback).
 *
 * Native Android playback now prefers passing YouTube watch URLs directly to the
 * BackgroundAudio plugin, which resolves playable streams on-device.
 *
 * This module remains for web/legacy fallback paths and should not be the primary
 * resolver for native playback.
 */

const SERVER_BASE = 'https://voicechat.tyranno.xyz';

export interface StreamInfo {
	audioUrl: string;
	title: string;
	duration: number;
}

export async function resolveStream(videoId: string, timeoutMs = 12000): Promise<StreamInfo> {
	const ctrl = new AbortController();
	const timer = setTimeout(() => ctrl.abort(), timeoutMs);
	try {
		const res = await fetch(`${SERVER_BASE}/api/youtube/stream?videoId=${encodeURIComponent(videoId)}`, {
			signal: ctrl.signal,
		});
		clearTimeout(timer);
		if (!res.ok) throw new Error(`HTTP ${res.status}`);
		const data = await res.json();
		if (!data.audioUrl) throw new Error('No audioUrl in response');
		return { audioUrl: data.audioUrl, title: data.title || videoId, duration: data.duration || 0 };
	} catch (e: any) {
		clearTimeout(timer);
		throw new Error(`Stream resolve failed for ${videoId}: ${e.message}`);
	}
}

export async function resolvePlaylist(
	tracks: Array<{ videoId: string; title: string }>,
	onProgress?: (i: number, total: number) => void
): Promise<Array<{ videoId: string; title: string; audioUrl: string }>> {
	const result = [];
	for (let i = 0; i < tracks.length; i++) {
		onProgress?.(i, tracks.length);
		try {
			const info = await resolveStream(tracks[i].videoId);
			result.push({ videoId: tracks[i].videoId, title: info.title || tracks[i].title, audioUrl: info.audioUrl });
		} catch {
			// skip unresolvable tracks
		}
	}
	return result;
}
