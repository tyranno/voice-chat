<script lang="ts">
	import { goto } from '$app/navigation';
	import { onMount, onDestroy } from 'svelte';
	import { tasks } from '$lib/stores/tasks.svelte';
	import { startTask } from '$lib/api/tasks';
	import TaskCard from '$lib/components/TaskCard.svelte';

	let promptInput = $state('');
	let maxIter = $state(30);
	let promiseText = $state('DONE');

	function onBack() { goto('/'); }
	onMount(() => window.addEventListener('hardwareBackPress', onBack));
	onDestroy(() => window.removeEventListener('hardwareBackPress', onBack));

	function submit() {
		const p = promptInput.trim();
		if (!p) return;
		startTask({ prompt: p, maxIterations: maxIter, completionPromise: promiseText });
		promptInput = '';
	}
</script>

<div class="app-container bg-gray-950 text-white">
	<header class="flex-shrink-0 flex items-center gap-3 px-4 py-3 bg-gray-900 border-b border-gray-800">
		<button onclick={() => goto('/')} class="p-2 rounded-lg hover:bg-gray-800 transition-colors">←</button>
		<span class="text-xl">🦖</span>
		<span class="font-semibold text-lg">AI 작업</span>
		{#if tasks.active.length > 0}
			<span class="ml-auto text-xs text-emerald-400">{tasks.active.length}개 실행 중</span>
		{:else if tasks.tasks.length > 0}
			<button onclick={() => tasks.clearFinished()} class="ml-auto text-xs text-gray-500 hover:text-gray-300">완료 지우기</button>
		{/if}
	</header>

	<div class="flex-1 overflow-y-auto px-4 py-4 space-y-3">
		{#if tasks.tasks.length === 0}
			<div class="text-center py-16 text-gray-500">
				<p class="text-5xl mb-3">🦖</p>
				<p class="text-sm">맡길 작업을 아래에 입력하세요</p>
				<p class="text-xs text-gray-600 mt-2">예: "현재 폴더 .ts 파일을 모두 분석해서 report.md를 만들어줘"</p>
			</div>
		{/if}

		{#each tasks.tasks as task (task.id)}
			<TaskCard {task} onCancel={() => task.cancel?.()} />
		{/each}
	</div>

	<div class="flex-shrink-0 px-4 pb-4 pt-2 bg-gray-950" style="padding-bottom: max(1rem, env(safe-area-inset-bottom));">
		<div class="space-y-2">
			<textarea
				bind:value={promptInput}
				placeholder="작업 설명 (예: 보고서 작성, 파일 정리, 분석...)"
				rows="3"
				class="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-emerald-500 resize-none"
			></textarea>
			<div class="flex items-center gap-2 text-xs">
				<label class="text-gray-400 flex items-center gap-1">
					최대 반복:
					<input type="number" bind:value={maxIter} min="1" max="100" class="w-14 px-2 py-1 bg-gray-800 border border-gray-700 rounded text-white" />
				</label>
				<label class="text-gray-400 flex items-center gap-1 flex-1">
					완료 키워드:
					<input type="text" bind:value={promiseText} class="flex-1 min-w-0 px-2 py-1 bg-gray-800 border border-gray-700 rounded text-white" />
				</label>
			</div>
			<button
				onclick={submit}
				disabled={!promptInput.trim()}
				class="w-full px-4 py-3 bg-emerald-500 hover:bg-emerald-400 disabled:bg-gray-700 disabled:text-gray-500 rounded-xl font-medium transition-colors"
			>
				🦖 Rex에게 맡기기
			</button>
		</div>
	</div>
</div>
