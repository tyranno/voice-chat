<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { bgAudio } from '$lib/stores/backgroundAudio.svelte';
	import { pause as bgPause, resume as bgResume, stop as bgStop } from '$lib/audio/backgroundAudio';

	// /music 페이지에서는 자체 player UI가 있으니 숨김 (중복 방지)
	const hideOnRoute = $derived(page.url.pathname === '/music');
	const show = $derived(!hideOnRoute && (bgAudio.isActive || bgAudio.isPausedReady));
</script>

{#if show}
	<div
		class="fixed left-0 right-0 z-[90] px-2"
		style="bottom: max(0.25rem, env(safe-area-inset-bottom));"
	>
		<div
			role="button" tabindex="0"
			onclick={() => goto('/music')}
			onkeydown={(e) => { if (e.key === 'Enter') goto('/music'); }}
			class="mx-auto max-w-md flex items-center gap-1.5 px-2 py-1 rounded-xl bg-emerald-900/85 border border-emerald-700/60 shadow-lg backdrop-blur cursor-pointer"
		>
			<span class="text-sm flex-shrink-0">
				{#if bgAudio.state === 'buffering'}⏳
				{:else if bgAudio.state === 'playing' || bgAudio.playWhenReady}🎵
				{:else}⏸{/if}
			</span>
			<p class="text-xs text-white truncate flex-1 min-w-0">{bgAudio.title || '재생'}</p>
			{#if bgAudio.state === 'playing' || bgAudio.playWhenReady}
				<button onclick={(e) => { e.stopPropagation(); bgPause(); }} class="flex-shrink-0 p-1 rounded hover:bg-emerald-700 text-white text-xs" aria-label="일시정지">⏸</button>
			{:else}
				<button onclick={(e) => { e.stopPropagation(); bgResume(); }} class="flex-shrink-0 p-1 rounded hover:bg-emerald-700 text-white text-xs" aria-label="재생">▶</button>
			{/if}
			<button onclick={(e) => { e.stopPropagation(); bgStop(); bgAudio.reset(); }} class="flex-shrink-0 p-1 rounded hover:bg-red-700 text-white text-xs" aria-label="정지">⏹</button>
		</div>
	</div>
{/if}
