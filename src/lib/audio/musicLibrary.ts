/**
 * MusicLibrary - 로컬 Music/Rex/ 폴더에 트랙 저장 + 시스템 플레이어 등록
 */
import { Capacitor, registerPlugin } from '@capacitor/core';

export interface SaveTrackOptions {
	url: string;
	title: string;
	artist?: string;
	filename?: string;
	mimeType?: string;
}

export interface SavedTrack {
	id?: number;
	uri: string;
	displayName?: string;
	title?: string;
	artist?: string;
	durationMs?: number;
	sizeBytes?: number;
	// Debug fields (per-fallback duration probe results)
	debug_mediaStoreDurationMs?: number;
	debug_mmrDurationMs?: number;
	debug_mediaPlayerDurationMs?: number;
}

interface MusicLibraryPlugin {
	saveTrack(options: SaveTrackOptions): Promise<{ uri: string; filename: string; size: number }>;
	cancelSave(): Promise<{ cancelled: boolean }>;
	listTracks(): Promise<{ tracks: SavedTrack[] }>;
	deleteTrack(options: { uri: string }): Promise<{ success: boolean }>;
	addListener(
		event: 'saveProgress',
		fn: (data: { downloaded: number; total: number; progress: number }) => void
	): Promise<{ remove: () => Promise<void> }>;
}

const MusicLibrary = registerPlugin<MusicLibraryPlugin>('MusicLibrary');

export const isNativeMusicLibrary = () => Capacitor.isNativePlatform();

/**
 * Save a YouTube track via server proxy URL.
 * Returns the saved file URI (MediaStore content URI on Android 10+).
 */
export async function saveTrack(opts: SaveTrackOptions) {
	return MusicLibrary.saveTrack(opts);
}

export async function cancelSave() {
	return MusicLibrary.cancelSave();
}

export async function listSavedTracks(): Promise<SavedTrack[]> {
	const r = await MusicLibrary.listTracks();
	return r.tracks || [];
}

export async function deleteSavedTrack(uri: string) {
	return MusicLibrary.deleteTrack({ uri });
}

export async function onSaveProgress(
	cb: (data: { downloaded: number; total: number; progress: number }) => void
) {
	const h = await MusicLibrary.addListener('saveProgress', cb);
	return () => h.remove();
}
