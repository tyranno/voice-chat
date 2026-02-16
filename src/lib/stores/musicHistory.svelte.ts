/**
 * Music play history — stored on server via conversations-style API
 */

const MAX_HISTORY = 100;

export interface MusicHistoryItem {
	videoId: string;
	title: string;
	playedAt: number;
}

export interface MusicPlaylist {
	id: string;
	query: string;
	items: Array<{ videoId: string; title: string }>;
	createdAt: number;
}

let history = $state<MusicHistoryItem[]>([]);
let playlists = $state<MusicPlaylist[]>([]);

// localStorage 기반 (음악 히스토리는 로컬로 충분)
function load() {
	try {
		const h = localStorage.getItem('vc_music_history');
		if (h) history = JSON.parse(h);
		const p = localStorage.getItem('vc_music_playlists');
		if (p) playlists = JSON.parse(p);
	} catch {}
}

function saveHistory() {
	try { localStorage.setItem('vc_music_history', JSON.stringify(history)); } catch {}
}

function savePlaylists() {
	try { localStorage.setItem('vc_music_playlists', JSON.stringify(playlists)); } catch {}
}

export function initMusicHistory() {
	load();
}

export function addToHistory(videoId: string, title: string) {
	// Remove duplicate
	history = history.filter(h => h.videoId !== videoId);
	// Add to front
	history.unshift({ videoId, title, playedAt: Date.now() });
	// Trim
	if (history.length > MAX_HISTORY) history = history.slice(0, MAX_HISTORY);
	saveHistory();
}

export function getHistory(): MusicHistoryItem[] {
	return history;
}

export function clearHistory() {
	history = [];
	saveHistory();
}

export function savePlaylist(query: string, items: Array<{ videoId: string; title: string }>) {
	// Avoid duplicate query
	playlists = playlists.filter(p => p.query !== query);
	playlists.unshift({
		id: String(Date.now()),
		query,
		items,
		createdAt: Date.now()
	});
	if (playlists.length > 20) playlists = playlists.slice(0, 20);
	savePlaylists();
}

export function getPlaylists(): MusicPlaylist[] {
	return playlists;
}

export function deletePlaylist(id: string) {
	playlists = playlists.filter(p => p.id !== id);
	savePlaylists();
}
