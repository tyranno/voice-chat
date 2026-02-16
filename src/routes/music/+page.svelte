<script lang="ts">
	import { goto } from '$app/navigation';
	import { onMount, onDestroy } from 'svelte';

	function onBackPress() { goto('/'); }
	onDestroy(() => window.removeEventListener('hardwareBackPress', onBackPress));
	import { page } from '$app/state';
	import { initMusicHistory, addToHistory, savePlaylist, getHistory, getPlaylists, deletePlaylist, clearHistory, type MusicPlaylist, type MusicHistoryItem } from '$lib/stores/musicHistory.svelte';

	let query = $state('');
	let searchResults = $state<Array<{ videoId: string; title: string; thumbnail: string }>>([]);
	let currentVideoId = $state<string | null>(null);
	let isSearching = $state(false);
	let searchError = $state('');
	let currentTitle = $state('');
	let showTab = $state<'search' | 'history' | 'playlists'>('search');
	let historyItems = $state<MusicHistoryItem[]>([]);
	let savedPlaylists = $state<MusicPlaylist[]>([]);

	function refreshData() {
		historyItems = getHistory();
		savedPlaylists = getPlaylists();
	}

	onMount(() => {
		window.addEventListener('hardwareBackPress', onBackPress);
		initMusicHistory();
		refreshData();
		const autoplay = page.url.searchParams.get('autoplay');
		const title = page.url.searchParams.get('title');
		if (autoplay) {
			currentVideoId = autoplay;
			currentTitle = title || '';
		}
	});

	async function searchYouTube() {
		if (!query.trim()) return;
		isSearching = true;
		searchError = '';
		searchResults = [];

		try {
			const encoded = encodeURIComponent(query.trim());
			// Use server proxy for reliable YouTube search
			const res = await fetch(`https://voicechat.tyranno.xyz/api/youtube/search?q=${encoded}`);
			if (!res.ok) throw new Error('검색 실패');
			const data = await res.json();
			searchResults = (data || []).slice(0, 20);
			if (searchResults.length === 0) {
				searchError = '검색 결과가 없습니다.';
			} else {
				// 검색 결과를 플레이리스트로 자동 저장
				savePlaylist(query.trim(), searchResults.map(r => ({ videoId: r.videoId, title: r.title })));
				refreshData();
			}
		} catch (e: any) {
			searchError = `검색 오류: ${e.message}`;
		} finally {
			isSearching = false;
		}
	}

	function playVideo(videoId: string, title?: string) {
		currentVideoId = videoId;
		if (title) {
			currentTitle = title;
			addToHistory(videoId, title);
			refreshData();
		}
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
</script>

<div class="flex flex-col h-screen bg-gray-950 text-white">
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
	<div class="px-4 py-3 flex gap-2 flex-shrink-0">
		<input
			type="text"
			bind:value={query}
			onkeydown={handleKeydown}
			placeholder="노래 검색..."
			class="flex-1 px-4 py-2.5 rounded-xl bg-gray-800 border border-gray-700 text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
		/>
		<button
			onclick={searchYouTube}
			disabled={isSearching}
			class="px-4 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 disabled:opacity-50 transition-colors font-medium"
		>
			{isSearching ? '...' : '🔍'}
		</button>
	</div>

	<!-- Player -->
	{#if currentVideoId}
		<div class="px-4 pb-3 flex-shrink-0">
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

	<!-- Tabs -->
	<div class="flex gap-1 px-4 pb-2 flex-shrink-0">
		<button onclick={() => showTab = 'search'} class="px-3 py-1.5 text-xs rounded-lg transition-colors {showTab === 'search' ? 'bg-blue-600 text-white' : 'bg-gray-800 text-gray-400'}">🔍 검색</button>
		<button onclick={() => { showTab = 'history'; refreshData(); }} class="px-3 py-1.5 text-xs rounded-lg transition-colors {showTab === 'history' ? 'bg-blue-600 text-white' : 'bg-gray-800 text-gray-400'}">⏱ 최근</button>
		<button onclick={() => { showTab = 'playlists'; refreshData(); }} class="px-3 py-1.5 text-xs rounded-lg transition-colors {showTab === 'playlists' ? 'bg-blue-600 text-white' : 'bg-gray-800 text-gray-400'}">📋 리스트</button>
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
					<button
						onclick={() => playVideo(result.videoId, result.title)}
						class="w-full flex items-center gap-3 p-2.5 rounded-xl hover:bg-gray-800/70 transition-colors text-left {currentVideoId === result.videoId ? 'bg-blue-900/30 border border-blue-700' : ''}"
					>
						<img src={result.thumbnail} alt="" class="w-24 h-16 rounded-lg object-cover flex-shrink-0 bg-gray-800" />
						<span class="text-sm line-clamp-2">{result.title}</span>
					</button>
				{/each}
			</div>

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
							class="w-full flex items-center gap-3 p-2.5 rounded-xl hover:bg-gray-800/70 transition-colors text-left {currentVideoId === item.videoId ? 'bg-blue-900/30 border border-blue-700' : ''}"
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
		{/if}
	</div>
</div>
