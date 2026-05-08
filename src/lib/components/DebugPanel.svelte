<script lang="ts">
	import { debug } from '$lib/stores/debug.svelte';

	let open = $state(false);
</script>

<button
	onclick={() => (open = !open)}
	class="fixed bottom-2 right-2 z-[150] w-10 h-10 rounded-full bg-gray-800/80 hover:bg-gray-700 border border-gray-700 text-xs text-gray-300 shadow-lg backdrop-blur"
	style="margin-bottom: env(safe-area-inset-bottom);"
	aria-label="Debug panel toggle"
	title="Developer log"
>{open ? '🛠' : '🐛'}</button>

{#if open}
	<div
		class="fixed bottom-14 right-2 left-2 max-w-md ml-auto z-[150] bg-gray-900/95 border border-gray-700 rounded-xl shadow-2xl backdrop-blur"
		style="margin-bottom: env(safe-area-inset-bottom);"
	>
		<div class="flex items-center justify-between px-3 py-2 border-b border-gray-800">
			<span class="text-xs text-gray-300 font-medium">개발자 로그</span>
			<div class="flex gap-1">
				<button onclick={() => debug.clear()} class="text-xs text-gray-500 hover:text-white px-2">지우기</button>
				<button onclick={() => (open = false)} class="text-xs text-gray-500 hover:text-white px-2" aria-label="닫기">✕</button>
			</div>
		</div>
		<pre class="text-[10px] text-gray-400 p-3 overflow-auto max-h-64 whitespace-pre-wrap break-all">{debug.log || '(아직 로그 없음)'}</pre>
	</div>
{/if}
