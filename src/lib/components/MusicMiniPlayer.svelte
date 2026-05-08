<script lang="ts">
	interface PlaylistItem {
		videoId: string;
		title: string;
		audioUrl?: string;
	}
	interface Props {
		musicVideoId: string;
		musicTitle: string;
		musicPlaylist: PlaylistItem[];
		musicIndex: number;
		musicSpeed: number;
		musicExpanded: boolean;
		musicIframe: HTMLIFrameElement | null;
		onPrev: () => void;
		onNext: () => void;
		onPause: () => void;
		onResume: () => void;
		onStop: () => void;
		onSetSpeed: (rate: number) => void;
		onSetExpanded: (expanded: boolean) => void;
	}
	let {
		musicVideoId, musicTitle, musicPlaylist, musicIndex, musicSpeed, musicExpanded,
		musicIframe = $bindable(),
		onPrev, onNext, onPause, onResume, onStop, onSetSpeed, onSetExpanded
	}: Props = $props();
</script>

{#if musicExpanded}
	<!-- 전체 화면 -->
	<div
		class="fixed inset-0 z-50 bg-black flex flex-col"
		style="padding-top: env(safe-area-inset-top); padding-bottom: env(safe-area-inset-bottom);"
	>
		<div class="flex items-center justify-between px-4 py-3 bg-gray-900">
			<div class="flex items-center gap-2 flex-1 min-w-0">
				<span class="text-lg">🎵</span>
				<p class="text-sm text-white truncate">{musicTitle || '재생 중'}</p>
				<span class="text-xs text-gray-500">{musicIndex + 1}/{musicPlaylist.length}</span>
			</div>
			<div class="flex gap-2">
				<button onclick={() => onSetExpanded(false)} class="px-3 py-1.5 text-xs bg-gray-700 hover:bg-gray-600 rounded-lg">▼ 축소</button>
				<button onclick={onStop} class="px-3 py-1.5 text-xs bg-red-700 hover:bg-red-600 rounded-lg">⏹</button>
			</div>
		</div>
		<!-- 컨트롤 바 -->
		<div class="flex items-center justify-center gap-4 px-4 py-2 bg-gray-900/80">
			<button onclick={onPrev} disabled={musicIndex <= 0} class="px-3 py-2 text-lg bg-gray-700 hover:bg-gray-600 rounded-lg disabled:opacity-30">⏮</button>
			<button onclick={onPause} class="px-3 py-2 text-lg bg-gray-700 hover:bg-gray-600 rounded-lg">⏸</button>
			<button onclick={onResume} class="px-3 py-2 text-lg bg-gray-700 hover:bg-gray-600 rounded-lg">▶</button>
			<button onclick={onNext} disabled={musicIndex >= musicPlaylist.length - 1} class="px-3 py-2 text-lg bg-gray-700 hover:bg-gray-600 rounded-lg disabled:opacity-30">⏭</button>
			<select
				onchange={(e) => onSetSpeed(parseFloat((e.target as HTMLSelectElement).value))}
				class="px-2 py-2 text-xs bg-gray-700 rounded-lg text-white"
			>
				<option value="0.5" selected={musicSpeed === 0.5}>0.5x</option>
				<option value="0.75" selected={musicSpeed === 0.75}>0.75x</option>
				<option value="1" selected={musicSpeed === 1.0}>1x</option>
				<option value="1.25" selected={musicSpeed === 1.25}>1.25x</option>
				<option value="1.5" selected={musicSpeed === 1.5}>1.5x</option>
				<option value="2" selected={musicSpeed === 2.0}>2x</option>
			</select>
		</div>
		<div class="flex-1 relative">
			<iframe
				bind:this={musicIframe}
				src={`https://www.youtube.com/embed/${musicVideoId}?autoplay=1&playsinline=1&enablejsapi=1&origin=${encodeURIComponent('https://localhost')}`}
				style="position: absolute; top: 0; left: 0; width: 100%; height: 100%;"
				allow="autoplay; encrypted-media"
				allowfullscreen
				title="Music Player"
			></iframe>
		</div>
	</div>
{:else}
	<!-- 미니 플레이어 -->
	<div class="flex-shrink-0 bg-gray-900 border-t border-gray-800 px-3 py-2">
		<div class="flex items-center gap-1.5">
			<button onclick={onPrev} disabled={musicIndex <= 0} class="p-1 text-sm disabled:opacity-30">⏮</button>
			<span class="text-sm">🎵</span>
			<p class="flex-1 text-xs text-gray-300 truncate">
				{musicTitle || '재생 중'}
				<span class="text-gray-500">({musicIndex + 1}/{musicPlaylist.length})</span>
			</p>
			<button onclick={onNext} disabled={musicIndex >= musicPlaylist.length - 1} class="p-1 text-sm disabled:opacity-30">⏭</button>
			<button onclick={() => onSetExpanded(true)} class="px-2 py-1 text-xs bg-gray-700 hover:bg-gray-600 rounded-lg">▲</button>
			<button onclick={onStop} class="px-2 py-1 text-xs bg-red-700 hover:bg-red-600 rounded-lg">⏹</button>
		</div>
		<div class="mt-1 rounded-lg overflow-hidden" style="height: 0; padding-bottom: 20%; position: relative;">
			<iframe
				bind:this={musicIframe}
				src={`https://www.youtube.com/embed/${musicVideoId}?autoplay=1&playsinline=1&enablejsapi=1&origin=${encodeURIComponent('https://localhost')}`}
				style="position: absolute; top: 0; left: 0; width: 100%; height: 100%;"
				allow="autoplay; encrypted-media"
				allowfullscreen
				title="Music Player"
			></iframe>
		</div>
	</div>
{/if}
