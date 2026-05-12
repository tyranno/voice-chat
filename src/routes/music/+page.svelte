<script lang="ts">
	import { goto } from '$app/navigation';
	import { onMount, onDestroy } from 'svelte';
	import { Capacitor } from '@capacitor/core';
	import {
		play as bgPlay, pause as bgPause, resume as bgResume, stop as bgStop,
		next as bgNext, prev as bgPrev, seek as bgSeek, setRate as bgSetRate, onStatus as bgOnStatus
	} from '$lib/audio/backgroundAudio';

	function onBackPress() { goto('/'); }
	onDestroy(() => {
		window.removeEventListener('hardwareBackPress', onBackPress);
		removeBgListener?.();
		saveProgressUnsub?.();
	});
	import { page } from '$app/state';
	import { initMusicHistory, addToHistory, savePlaylist, getHistory, getPlaylists, deletePlaylist, clearHistory, type MusicPlaylist, type MusicHistoryItem } from '$lib/stores/musicHistory.svelte';
	import { saveTrack, cancelSave, listSavedTracks, deleteSavedTrack, onSaveProgress, type SavedTrack } from '$lib/audio/musicLibrary';
	import { toast } from '$lib/stores/toast.svelte';
	import { settings } from '$lib/stores/settings.svelte';

	const isNative = Capacitor.isNativePlatform();

	let query = $state('');
	let searchResults = $state<Array<{ videoId: string; title: string; thumbnail: string }>>([]);
	let currentVideoId = $state<string | null>(null);
	let isSearching = $state(false);
	let searchError = $state('');
	let currentTitle = $state('');
	let playbackMode = $state<'foreground' | 'background'>('background');
	let playbackRate = $state(1.0);
	async function changeRate(r: number) {
		playbackRate = r;
		if (isNative && playbackMode === 'background') {
			try { await bgSetRate(r); } catch {}
		}
	}

	function openInYouTube(videoId: string) {
		// Android: 시스템 인텐트로 처리되어 YouTube 앱이 있으면 자동으로 열림
		const url = `https://m.youtube.com/watch?v=${encodeURIComponent(videoId)}`;
		window.open(url, '_blank');
	}
	let showTab = $state<'search' | 'history' | 'playlists' | 'saved'>('search');
	let historyItems = $state<MusicHistoryItem[]>([]);
	let savedPlaylists = $state<MusicPlaylist[]>([]);
	let savedTracks = $state<SavedTrack[]>([]);
	// videoId → progress% (0~100, -1 = unknown, 100 = done)
	let savingProgress = $state<Record<string, number>>({});
	let saveProgressUnsub: (() => void) | null = null;
	// remember the active save target so we know what videoId the progress event maps to
	let activeSaveVideoId = '';

	// Native-only state
	let isResolving = $state(false);
	let bgPlaying = $state(false);
	let bgPlayWhenReady = $state(false);
	let bgState = $state<'idle' | 'buffering' | 'ready' | 'playing' | 'paused' | 'ended' | 'error'>('idle');
	let bgBuffering = $state(false);
	let bgError = $state('');
	let bgIndex = $state(0);
	let bgHasNext = $state(false);
	let bgHasPrev = $state(false);
	let bgPositionMs = $state(0);
	let bgDurationMs = $state(0);
	let removeBgListener: (() => void) | null = null;
	let bgBroadcastCount = $state(0); // diagnostic: how many status broadcasts received
	let lastBroadcastAt = $state(0);
	// Local "user intends to play" flag — true between bgPlay and bgPause/bgStop. This is
	// independent of bgPlaying (which comes from native broadcasts that may be unreliable),
	// so the ticker keeps running even if no broadcasts arrive.
	let userPlaying = $state(false);

	// Position ticker — every 250ms.
	// If a fresh broadcast (<1.5s old) updated bgPositionMs, that's authoritative.
	// Otherwise advance locally at playbackRate so the thumb moves regardless.
	$effect(() => {
		if (userPlaying && bgDurationMs > 0) {
			const id = setInterval(() => {
				const now = Date.now();
				if (now - lastBroadcastAt > 1500 && bgPositionMs < bgDurationMs) {
					bgPositionMs = Math.min(bgPositionMs + 250 * (playbackRate || 1.0), bgDurationMs);
				}
			}, 250);
			return () => clearInterval(id);
		}
	});

	function refreshData() {
		historyItems = getHistory();
		savedPlaylists = getPlaylists();
	}

	async function refreshSavedTracks() {
		if (!isNative) return;
		try {
			savedTracks = await listSavedTracks();
		} catch (e: any) {
			console.warn('listSavedTracks failed', e);
		}
	}

	async function saveCurrentOrTrack(videoId: string, title: string) {
		if (!isNative) {
			toast.warning('네이티브 앱에서만 저장 가능');
			return;
		}
		if (savingProgress[videoId] !== undefined && savingProgress[videoId] < 100) {
			// Already saving — second click cancels
			try {
				await cancelSave();
				toast.info('다운로드 취소 요청');
			} catch {}
			return;
		}
		const url = `${settings.serverUrl}/api/youtube/proxy?videoId=${encodeURIComponent(videoId)}`;
		savingProgress = { ...savingProgress, [videoId]: 0 };
		activeSaveVideoId = videoId;
		try {
			const res = await saveTrack({
				url,
				title,
				artist: 'YouTube',
				mimeType: 'audio/mp4',
			});
			savingProgress = { ...savingProgress, [videoId]: 100 };
			toast.success(`저장됨: ${title}`);
			void res;
			await refreshSavedTracks();
		} catch (e: any) {
			delete savingProgress[videoId];
			savingProgress = { ...savingProgress };
			toast.error(`저장 실패: ${e?.message || e}`);
		}
	}

	async function playSavedTrack(t: SavedTrack) {
		if (!isNative) {
			toast.warning('네이티브 앱에서만 재생 가능');
			return;
		}
		const title = t.title || t.displayName || '저장된 트랙';
		// CRITICAL: set duration up-front from listTracks data (which we know works).
		// This way the controller slider works immediately, regardless of what the
		// service broadcasts — broadcasts only refine, never override our trusted value.
		const knownDuration = (t.durationMs && t.durationMs > 0) ? t.durationMs : 0;
		if (knownDuration > 0) {
			bgDurationMs = knownDuration;
			bgPositionMs = 0;
		}
		userPlaying = true;
		try {
			await bgPlay({
				url: t.uri,
				title,
				artist: (t.artist && t.artist !== '<unknown>') ? t.artist : 'Rex',
				playlist: [t.uri],
				index: 0,
				durationMs: knownDuration,
			} as any);
			playbackMode = 'background';
			currentVideoId = `saved:${t.id ?? t.uri}`;
			currentTitle = title;
			playbackRate = 1.0;
			toast.success(`재생: ${title}`);
		} catch (e: any) {
			toast.error(`재생 실패: ${e?.message || e}`);
		}
	}

	function isCurrentSavedTrack() {
		return currentVideoId?.startsWith('saved:') ?? false;
	}

	async function deleteSaved(uri: string, name: string) {
		if (!confirm(`"${name}" 을 삭제할까요?`)) return;
		try {
			await deleteSavedTrack(uri);
			toast.info(`삭제됨: ${name}`);
			await refreshSavedTracks();
		} catch (e: any) {
			toast.error(`삭제 실패: ${e?.message || e}`);
		}
	}

	async function deleteAllSaved() {
		if (savedTracks.length === 0) return;
		if (!confirm(`저장된 ${savedTracks.length}곡을 모두 삭제할까요?`)) return;
		let ok = 0, fail = 0;
		for (const t of savedTracks) {
			try { await deleteSavedTrack(t.uri); ok++; } catch { fail++; }
		}
		await refreshSavedTracks();
		if (fail > 0) toast.warning(`${ok}곡 삭제, ${fail}곡 실패`);
		else toast.success(`${ok}곡 모두 삭제됨`);
	}

	function fmtBytes(b: number) {
		if (!b) return '';
		if (b < 1024) return b + ' B';
		if (b < 1024 * 1024) return (b / 1024).toFixed(1) + ' KB';
		return (b / 1024 / 1024).toFixed(1) + ' MB';
	}

	onMount(async () => {
		window.addEventListener('hardwareBackPress', onBackPress);
		initMusicHistory();
		refreshData();
		const autoplay = page.url.searchParams.get('autoplay');
		const title = page.url.searchParams.get('title');
		if (autoplay) {
			await playVideo(autoplay, title || '');
		}

		// Subscribe save progress (updates savingProgress for the active save)
		if (isNative) {
			saveProgressUnsub = await onSaveProgress((d) => {
				if (activeSaveVideoId) {
					savingProgress = { ...savingProgress, [activeSaveVideoId]: d.progress };
				}
			});
			await refreshSavedTracks();
		}

		// Listen to native background audio status
		if (isNative) {
			removeBgListener = await bgOnStatus((s) => {
				bgPlaying = s.playing;
				bgPlayWhenReady = s.playWhenReady ?? s.playing;
				if (s.state) bgState = s.state;
				bgBuffering = s.buffering ?? false;
				bgHasNext = s.hasNext ?? false;
				bgHasPrev = s.hasPrev ?? false;
				if (s.index !== undefined) bgIndex = s.index;
				if (s.error) bgError = s.error;
				if (s.title) currentTitle = s.title;
				// Coerce defensively: Capacitor sometimes serializes long values as strings.
				const posRaw: any = s.positionMs;
				const durRaw: any = s.durationMs;
				const pos = typeof posRaw === 'number' ? posRaw : (typeof posRaw === 'string' ? parseInt(posRaw, 10) : NaN);
				const dur = typeof durRaw === 'number' ? durRaw : (typeof durRaw === 'string' ? parseInt(durRaw, 10) : NaN);
				bgBroadcastCount++;
				lastBroadcastAt = Date.now();
				if (!isNaN(pos) && pos > 0) bgPositionMs = pos; // only override if broadcast carries real value
				// NEVER let a 0 broadcast clobber a known duration — service can emit 0
				// during state transitions (IDLE/BUFFERING) before metadata is parsed.
				// We already set bgDurationMs from list data in playSavedTrack, trust that.
				if (!isNaN(dur) && dur > 0) bgDurationMs = Math.max(bgDurationMs, dur);
			});
		}
	});

	// Pagination state for infinite scroll
	let searchOffset = $state(0);
	let isLoadingMore = $state(false);
	let hasMoreResults = $state(true);
	const PAGE_SIZE = 50;

	async function searchYouTube() {
		if (!query.trim()) return;
		isSearching = true;
		searchError = '';
		searchResults = [];
		searchOffset = 0;
		hasMoreResults = true;

		try {
			const encoded = encodeURIComponent(query.trim());
			const res = await fetch(`https://voicechat.tyranno.xyz/api/youtube/search?q=${encoded}&offset=0&limit=${PAGE_SIZE}`);
			if (!res.ok) throw new Error('검색 실패');
			const data = await res.json();
			searchResults = data || [];
			searchOffset = searchResults.length;
			if (searchResults.length === 0) {
				searchError = '검색 결과가 없습니다.';
				hasMoreResults = false;
			} else {
				if (searchResults.length < PAGE_SIZE) hasMoreResults = false;
				savePlaylist(query.trim(), searchResults.map(r => ({ videoId: r.videoId, title: r.title })));
				refreshData();
			}
		} catch (e: any) {
			searchError = `검색 오류: ${e.message}`;
		} finally {
			isSearching = false;
		}
	}

	async function loadMoreSearchResults() {
		if (isLoadingMore || !hasMoreResults || !query.trim()) return;
		isLoadingMore = true;
		try {
			const encoded = encodeURIComponent(query.trim());
			const res = await fetch(`https://voicechat.tyranno.xyz/api/youtube/search?q=${encoded}&offset=${searchOffset}&limit=${PAGE_SIZE}`);
			if (!res.ok) throw new Error('추가 검색 실패');
			const data = await res.json();
			const newItems = (data || []) as typeof searchResults;
			if (newItems.length === 0) {
				hasMoreResults = false;
			} else {
				searchResults = [...searchResults, ...newItems];
				searchOffset = searchResults.length;
				if (newItems.length < PAGE_SIZE) hasMoreResults = false;
			}
		} catch (e: any) {
			// silent fail on pagination — keep what we have
		} finally {
			isLoadingMore = false;
		}
	}

	// IntersectionObserver-based "load more" sentinel
	let sentinelEl: HTMLDivElement | undefined = $state();
	$effect(() => {
		if (!sentinelEl || showTab !== 'search') return;
		const observer = new IntersectionObserver((entries) => {
			for (const e of entries) {
				if (e.isIntersecting) loadMoreSearchResults();
			}
		}, { rootMargin: '200px' });
		observer.observe(sentinelEl);
		return () => observer.disconnect();
	});

	async function playVideo(videoId: string, title?: string) {
		currentVideoId = videoId;
		currentTitle = title || '';
		if (title) { addToHistory(videoId, title); refreshData(); }

		if (!isNative) return; // web: iframe handles it

		// Native: pass YouTube watch URLs to plugin (plugin resolves to playable stream)
		isResolving = true;
		bgError = '';
		// Reset position for the new track so the slider starts fresh
		bgPositionMs = 0;
		userPlaying = true;
		try {
			const playlist = searchResults.length > 1
				? searchResults.map(r => ({ videoId: r.videoId, title: r.title }))
				: [{ videoId, title: title || '' }];
			const idx = playlist.findIndex(r => r.videoId === videoId);
			const safeIdx = idx >= 0 ? idx : 0;
			const watchUrls = playlist.map((r) => `https://www.youtube.com/watch?v=${encodeURIComponent(r.videoId)}`);

			// Pre-fetch duration from /api/youtube/stream so the controller slider is usable
			// from the moment playback starts — no waiting for native broadcasts.
			let durHintMs = 0;
			try {
				const sres = await fetch(`${settings.serverUrl}/api/youtube/stream?videoId=${encodeURIComponent(videoId)}`);
				if (sres.ok) {
					const sdata = await sres.json();
					if (sdata?.duration && sdata.duration > 0) {
						durHintMs = Math.round(sdata.duration * 1000);
						bgDurationMs = durHintMs;
					}
				}
			} catch {}

			await bgPlay({
				url: watchUrls[safeIdx],
				title: title || videoId,
				artist: 'YouTube',
				playlist: watchUrls,
				index: safeIdx,
				durationMs: durHintMs,
			} as any);
		} catch (e: any) {
			bgError = `스트림 오류: ${e.message}`;
		} finally {
			isResolving = false;
		}
	}

	function fmtTime(ms: number) {
		const totalSec = Math.max(0, Math.floor(ms / 1000));
		const h = Math.floor(totalSec / 3600);
		const m = Math.floor((totalSec % 3600) / 60);
		const s = totalSec % 60;
		if (h > 0) {
			return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
		}
		return `${m}:${String(s).padStart(2, '0')}`;
	}

	async function onSeekInput(e: Event) {
		const value = Number((e.target as HTMLInputElement).value || 0);
		bgPositionMs = value;
	}

	async function onSeekCommit(e: Event) {
		const value = Number((e.target as HTMLInputElement).value || 0);
		bgPositionMs = value;
		await bgSeek(value).catch(() => {});
	}

	function loadPlaylist(pl: MusicPlaylist) {
		searchResults = pl.items.map(i => ({ ...i, thumbnail: `https://i.ytimg.com/vi/${i.videoId}/mqdefault.jpg` }));
		query = pl.query;
		showTab = 'search';
		if (pl.items.length > 0) playVideo(pl.items[0].videoId, pl.items[0].title);
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter') searchYouTube();
	}

	// "바로듣기" — 즉시 iframe 재생 (foreground only, 화면 켜져있을 때만)
	async function playForeground(videoId: string, title: string) {
		if (isNative) {
			try { await bgStop(); } catch {}
		}
		playbackMode = 'foreground';
		currentVideoId = videoId;
		currentTitle = title;
		if (title) { addToHistory(videoId, title); refreshData(); }
	}

	// "background로 듣기" — ExoPlayer 백그라운드 재생 (기존 playVideo)
	async function playBackground(videoId: string, title: string) {
		playbackMode = 'background';
		await playVideo(videoId, title);
	}

	// 검색창 focus + query 비어있을 때 최근 검색어 보여줌
	let searchFocused = $state(false);
	const recentSearches = $derived(
		savedPlaylists
			.map((p) => ({ id: p.id, query: p.query, count: p.items.length }))
			.slice(0, 12)
	);
	function applyRecentSearch(q: string) {
		query = q;
		searchFocused = false;
		searchYouTube();
	}
	function clearAllSearches() {
		if (!confirm('최근 검색어를 모두 지울까요?')) return;
		savedPlaylists.forEach((p) => deletePlaylist(p.id));
		refreshData();
	}
	function clearOneSearch(id: string, e: Event) {
		e.stopPropagation();
		deletePlaylist(id);
		refreshData();
	}
</script>

<div class="app-container bg-gray-950 text-white">
	<!-- Header -->
	<header class="flex items-center gap-3 px-4 py-3 bg-gray-900 border-b border-gray-800 flex-shrink-0">
		<button
			onclick={() => goto('/')}
			class="p-2 rounded-lg hover:bg-gray-800 transition-colors"
		>←</button>
		<span class="text-xl">🎵</span>
		<span class="font-semibold text-lg">음악</span>
	</header>

	<!-- Search -->
	<div class="px-4 py-3 flex-shrink-0 space-y-2">
		<div class="flex gap-2">
			<input
				type="text"
				bind:value={query}
				onkeydown={handleKeydown}
				onfocus={() => (searchFocused = true)}
				onblur={() => setTimeout(() => (searchFocused = false), 200)}
				placeholder="노래 검색..."
				class="flex-1 px-4 py-2.5 rounded-xl bg-gray-800 border border-gray-700 text-white placeholder-gray-500 focus:outline-none focus:border-emerald-500"
			/>
			<button
				onclick={searchYouTube}
				disabled={isSearching}
				class="px-4 py-2.5 rounded-xl bg-emerald-500 hover:bg-emerald-600 disabled:opacity-50 transition-colors font-medium"
			>
				{isSearching ? '...' : '🔍'}
			</button>
		</div>

		<!-- 최근 검색어 (검색창 포커스 + query 비어있을 때) -->
		{#if searchFocused && !query.trim() && recentSearches.length > 0}
			<div class="bg-gray-900/80 border border-gray-700 rounded-xl p-2 space-y-1">
				<div class="flex items-center justify-between px-2 pb-1">
					<span class="text-[10px] text-gray-500 uppercase tracking-wider">최근 검색</span>
					<button onclick={clearAllSearches} class="text-[10px] text-gray-500 hover:text-red-400 transition-colors">
						전체 삭제
					</button>
				</div>
				<div class="flex flex-wrap gap-1.5">
					{#each recentSearches as rs (rs.id)}
						<div class="inline-flex items-center bg-gray-800 hover:bg-gray-700 rounded-full text-xs overflow-hidden">
							<button
								onmousedown={() => applyRecentSearch(rs.query)}
								class="px-3 py-1.5 text-gray-200"
							>🔍 {rs.query}</button>
							<button
								onmousedown={(e) => clearOneSearch(rs.id, e)}
								class="px-2 py-1.5 text-gray-500 hover:text-red-400 border-l border-gray-700"
								aria-label="삭제"
							>✕</button>
						</div>
					{/each}
				</div>
			</div>
		{/if}
	</div>

	<!-- Player -->
	{#if currentVideoId}
		<div class="px-4 pb-3 flex-shrink-0">
			{#if isNative && playbackMode === 'background'}
				<!-- Native: ExoPlayer background audio (compact) -->
				<div class="rounded-xl bg-gray-800/80 border border-gray-700 p-2.5 space-y-2">
					<div class="flex items-center gap-2">
						<span class="text-base">{bgState === 'buffering' ? '⏳' : (bgState === 'playing' || (bgPlayWhenReady && bgState !== 'paused')) ? '🎵' : '⏸'}</span>
						<p class="text-sm text-white truncate flex-1 min-w-0">{currentTitle || currentVideoId}</p>
						{#if !isCurrentSavedTrack()}
							{@const vid = currentVideoId}
							{@const prog = vid ? savingProgress[vid] : undefined}
							<button
								onclick={() => vid && saveCurrentOrTrack(vid, currentTitle || vid)}
								title={prog !== undefined && prog < 100 ? '다시 누르면 취소' : '폰에 저장'}
								class="flex-shrink-0 px-2 py-1 text-xs rounded {prog !== undefined && prog < 100 ? 'bg-amber-700 hover:bg-red-700' : 'bg-gray-700 hover:bg-gray-600'}"
							>{#if prog === undefined}💾{:else if prog < 100}{prog >= 0 ? prog + '% ✕' : '⏳ ✕'}{:else}✅{/if}</button>
							<button onclick={() => currentVideoId && openInYouTube(currentVideoId)} title="YouTube" class="flex-shrink-0 px-2 py-1 text-xs rounded bg-red-700 hover:bg-red-600 text-white">▶️</button>
						{/if}
					</div>
					{#if bgError}<p class="text-xs text-red-400">{bgError}</p>{/if}
					<input
						type="range"
						min="0"
						max={Math.max(1, bgDurationMs)}
						value={Math.min(bgPositionMs, Math.max(1, bgDurationMs))}
						oninput={onSeekInput}
						onchange={onSeekCommit}
						class="w-full accent-emerald-500 h-1"
						disabled={bgDurationMs <= 0}
					/>
					<div class="flex items-center gap-2 text-[10px] text-gray-400">
						<span>{fmtTime(bgPositionMs)}</span>
						<span class="flex-1"></span>
						<span>{fmtTime(bgDurationMs)}</span>
					</div>
					{#if settings.developerMode}
						<p class="text-[10px] text-amber-400/70 font-mono">dur={bgDurationMs} pos={bgPositionMs} state={bgState} bc={bgBroadcastCount} since={lastBroadcastAt > 0 ? Math.round((Date.now() - lastBroadcastAt) / 1000) + 's' : 'never'}</p>
					{/if}
					<div class="flex items-center gap-1">
						<button onclick={() => { userPlaying = true; bgPrev(); }} disabled={!bgHasPrev} class="px-2 py-1 rounded disabled:opacity-30 hover:bg-gray-700 text-sm">⏮</button>
						{#if userPlaying || bgState === 'playing' || bgPlayWhenReady}
							<button onclick={() => { userPlaying = false; bgPause(); }} class="px-3 py-1 rounded bg-emerald-500 hover:bg-emerald-600 text-sm">⏸</button>
						{:else}
							<button onclick={() => { userPlaying = true; bgResume(); }} disabled={isResolving} class="px-3 py-1 rounded bg-emerald-500 hover:bg-emerald-600 disabled:opacity-50 text-sm">▶</button>
						{/if}
						<button onclick={() => { userPlaying = true; bgNext(); }} disabled={!bgHasNext} class="px-2 py-1 rounded disabled:opacity-30 hover:bg-gray-700 text-sm">⏭</button>
						<button onclick={() => { userPlaying = false; bgPositionMs = 0; bgStop(); }} class="px-2 py-1 rounded hover:bg-gray-700 text-sm">⏹</button>
						<span class="flex-1"></span>
						<select
							onchange={(e) => changeRate(parseFloat((e.target as HTMLSelectElement).value))}
							class="px-1 py-1 text-xs bg-gray-700 rounded text-white"
						>
							{#each [0.5, 0.75, 1.0, 1.25, 1.5, 2.0] as r}
								<option value={r} selected={playbackRate === r}>{r}x</option>
							{/each}
						</select>
					</div>
				</div>
			{:else}
				<!-- Foreground: YouTube iframe (즉시 재생, 화면 켜진 상태에만) -->
				<div class="space-y-2">
					{#if isNative}
						<div class="flex items-center justify-between text-xs text-gray-400 px-1">
							<span>▶ 바로듣기 (화면 켜진 상태에만)</span>
							<button
								onclick={() => currentVideoId && playBackground(currentVideoId, currentTitle)}
								class="px-2 py-1 bg-emerald-600 hover:bg-emerald-500 rounded-lg text-white"
							>🎵 백그라운드로 전환</button>
						</div>
					{/if}
					<div class="relative w-full rounded-xl overflow-hidden" style="padding-bottom: 56.25%;">
						<iframe
							src="https://www.youtube.com/embed/{currentVideoId}?autoplay=1&rel=0"
							title="YouTube player"
							class="absolute inset-0 w-full h-full"
							frameborder="0"
							allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
							allowfullscreen
						></iframe>
					</div>
				</div>
			{/if}
		</div>
	{/if}

	<!-- Tabs -->
	<div class="flex gap-1 px-4 pb-2 flex-shrink-0">
		<button onclick={() => showTab = 'search'} class="px-3 py-1.5 text-xs rounded-lg transition-colors {showTab === 'search' ? 'bg-emerald-500 text-white' : 'bg-gray-800 text-gray-400'}">🔍 검색</button>
		<button onclick={() => { showTab = 'history'; refreshData(); }} class="px-3 py-1.5 text-xs rounded-lg transition-colors {showTab === 'history' ? 'bg-emerald-500 text-white' : 'bg-gray-800 text-gray-400'}">⏱ 최근</button>
		<button onclick={() => { showTab = 'playlists'; refreshData(); }} class="px-3 py-1.5 text-xs rounded-lg transition-colors {showTab === 'playlists' ? 'bg-emerald-500 text-white' : 'bg-gray-800 text-gray-400'}">📋 리스트</button>
		{#if isNative}
			<button onclick={() => { showTab = 'saved'; refreshSavedTracks(); }} class="px-3 py-1.5 text-xs rounded-lg transition-colors {showTab === 'saved' ? 'bg-emerald-500 text-white' : 'bg-gray-800 text-gray-400'}">💾 저장됨 {#if savedTracks.length > 0}({savedTracks.length}){/if}</button>
		{/if}
	</div>

	<!-- Content -->
	<div class="flex-1 overflow-y-auto px-4 pb-4">
		{#if showTab === 'search'}
			{#if searchError}
				<p class="text-gray-400 text-center py-8 text-sm">{searchError}</p>
			{/if}

			{#if searchResults.length === 0 && !isSearching && !searchError}
				<div class="text-center py-16 text-gray-500">
					<p class="text-4xl mb-3">🎶</p>
					<p>YouTube에서 음악을 검색하세요</p>
				</div>
			{/if}

			<div class="space-y-2">
				{#each searchResults as result}
					{@const prog = savingProgress[result.videoId]}
					<div
						role="button" tabindex="0"
						onclick={() => playBackground(result.videoId, result.title)}
						onkeydown={(e) => { if (e.key === 'Enter') playBackground(result.videoId, result.title); }}
						class="w-full flex items-center gap-2 p-2.5 rounded-xl hover:bg-gray-800/70 transition-colors cursor-pointer {currentVideoId === result.videoId ? 'bg-emerald-900/30 border border-emerald-700' : ''}"
					>
						<img src={result.thumbnail} alt="" class="w-20 h-14 rounded-lg object-cover flex-shrink-0 bg-gray-800" />
						<span class="text-sm line-clamp-2 flex-1 min-w-0">{result.title}</span>
						<button
							onclick={(e) => { e.stopPropagation(); openInYouTube(result.videoId); }}
							title="YouTube에서 보기"
							class="flex-shrink-0 px-2 py-2 rounded-lg bg-red-700 hover:bg-red-600 transition-colors text-sm"
						>▶️</button>
						{#if isNative}
							<button
								onclick={(e) => { e.stopPropagation(); saveCurrentOrTrack(result.videoId, result.title); }}
								title={prog !== undefined && prog < 100 ? '다시 누르면 취소' : '폰에 저장'}
								class="flex-shrink-0 px-3 py-2 rounded-lg {prog !== undefined && prog < 100 ? 'bg-amber-700 hover:bg-red-700' : 'bg-gray-700 hover:bg-gray-600'} transition-colors text-sm min-w-[48px]"
							>
								{#if prog === undefined}💾
								{:else if prog < 100}<span class="text-[10px]">{prog >= 0 ? prog + '% ✕' : '⏳ ✕'}</span>
								{:else}✅{/if}
							</button>
						{/if}
					</div>
				{/each}
			</div>

			<!-- Infinite scroll sentinel + loading indicator -->
			{#if searchResults.length > 0}
				<div bind:this={sentinelEl} class="py-4 text-center text-xs text-gray-500">
					{#if isLoadingMore}
						⏳ 더 불러오는 중...
					{:else if hasMoreResults}
						<span class="opacity-50">↓ 스크롤하여 더 보기</span>
					{:else}
						<span class="opacity-30">— 모든 결과 표시됨 ({searchResults.length}곡) —</span>
					{/if}
				</div>
			{/if}

		{:else if showTab === 'history'}
			{#if historyItems.length > 0}
				<div class="flex justify-end mb-2">
					<button onclick={() => { clearHistory(); refreshData(); }} class="text-xs text-gray-500 hover:text-red-400 transition-colors">전체 삭제</button>
				</div>
			{/if}
			{#if historyItems.length === 0}
				<div class="text-center py-16 text-gray-500">
					<p class="text-4xl mb-3">⏱</p>
					<p>재생 기록이 없습니다</p>
				</div>
			{:else}
				<div class="space-y-2">
					{#each historyItems as item}
						<button
							onclick={() => playVideo(item.videoId, item.title)}
							class="w-full flex items-center gap-3 p-2.5 rounded-xl hover:bg-gray-800/70 transition-colors text-left {currentVideoId === item.videoId ? 'bg-emerald-900/30 border border-emerald-700' : ''}"
						>
							<img src={`https://i.ytimg.com/vi/${item.videoId}/mqdefault.jpg`} alt="" class="w-24 h-16 rounded-lg object-cover flex-shrink-0 bg-gray-800" />
							<div class="flex-1 min-w-0">
								<span class="text-sm line-clamp-2">{item.title}</span>
								<span class="text-xs text-gray-500">{new Date(item.playedAt).toLocaleDateString('ko-KR')} {new Date(item.playedAt).toLocaleTimeString('ko-KR', {hour:'2-digit', minute:'2-digit'})}</span>
							</div>
						</button>
					{/each}
				</div>
			{/if}

		{:else if showTab === 'playlists'}
			{#if savedPlaylists.length === 0}
				<div class="text-center py-16 text-gray-500">
					<p class="text-4xl mb-3">📋</p>
					<p>저장된 리스트가 없습니다</p>
				</div>
			{:else}
				<div class="space-y-2">
					{#each savedPlaylists as pl}
						<div class="flex items-center gap-2 p-3 rounded-xl bg-gray-800/50 hover:bg-gray-800 transition-colors">
							<button onclick={() => loadPlaylist(pl)} class="flex-1 text-left min-w-0">
								<p class="text-sm font-medium truncate">🔍 "{pl.query}"</p>
								<p class="text-xs text-gray-500">{pl.items.length}곡 · {new Date(pl.createdAt).toLocaleDateString('ko-KR')}</p>
							</button>
							<button onclick={() => { deletePlaylist(pl.id); refreshData(); }} class="p-1 text-gray-500 hover:text-red-400">🗑</button>
						</div>
					{/each}
				</div>
			{/if}

		{:else if showTab === 'saved'}
			<div class="flex items-center justify-between mb-2">
				<span class="text-[11px] text-gray-500">
					💾 폰의 <code class="text-gray-400">Music/Rex/</code> 폴더에 저장
				</span>
				{#if savedTracks.length > 0}
					<button
						onclick={deleteAllSaved}
						class="text-xs text-gray-500 hover:text-red-400 transition-colors"
					>🗑 전체 삭제 ({savedTracks.length})</button>
				{/if}
			</div>
			{#if savedTracks.length === 0}
				<div class="text-center py-16 text-gray-500">
					<p class="text-4xl mb-3">💾</p>
					<p>저장된 트랙이 없습니다</p>
					<p class="text-xs text-gray-600 mt-2">검색 결과 옆 💾 버튼으로 저장하세요</p>
				</div>
			{:else}
				<div class="space-y-2">
					{#each savedTracks as t (t.uri)}
						{@const isCurrent = currentVideoId === `saved:${t.id ?? t.uri}`}
						{@const cleanTitle = (t.title && t.title !== '<unknown>') ? t.title : (t.displayName ? t.displayName.replace(/\.(m4a|mp3|webm|ogg|aac)$/i, '') : '제목없음')}
						{@const cleanArtist = (t.artist && t.artist !== '<unknown>') ? t.artist : 'Rex'}
						<div
							role="button" tabindex="0"
							onclick={() => playSavedTrack(t)}
							onkeydown={(e) => { if (e.key === 'Enter') playSavedTrack(t); }}
							class="flex items-center gap-3 p-2.5 rounded-xl bg-gray-800/50 hover:bg-gray-800 transition-colors cursor-pointer {isCurrent ? 'border border-emerald-600 bg-emerald-900/20' : ''}"
						>
							<span class="text-2xl flex-shrink-0">{isCurrent ? '▶' : '🎵'}</span>
							<div class="flex-1 min-w-0">
								<p class="text-sm font-medium truncate">{cleanTitle}</p>
								<p class="text-xs text-gray-500 truncate">
									{cleanArtist}
									{#if t.sizeBytes}· {fmtBytes(t.sizeBytes)}{/if}
									{#if t.durationMs && t.durationMs > 0}· {fmtTime(t.durationMs)}{/if}
								</p>
								{#if settings.developerMode}
									<p class="text-[10px] text-amber-400/70 truncate font-mono">
										ms={t.durationMs ?? 0} MS={t.debug_mediaStoreDurationMs ?? 0} MMR={t.debug_mmrDurationMs ?? 0} MP={t.debug_mediaPlayerDurationMs ?? 0}
									</p>
								{/if}
							</div>
							<button
								onclick={(e) => { e.stopPropagation(); deleteSaved(t.uri, t.title || t.displayName || '트랙'); }}
								class="p-1 text-gray-500 hover:text-red-400"
								aria-label="삭제"
							>🗑</button>
						</div>
					{/each}
				</div>
			{/if}
		{/if}
	</div>
</div>
