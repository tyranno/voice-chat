<script lang="ts">
	import type { Task } from '$lib/stores/tasks.svelte';
	import { downloadFile } from '$lib/api/downloader';
	import { toast } from '$lib/stores/toast.svelte';

	interface Props {
		task: Task;
		onCancel?: () => void;
	}
	let { task, onCancel }: Props = $props();

	function statusColor(s: string) {
		switch (s) {
			case 'running':   return 'bg-emerald-500/20 border-emerald-500/40 text-emerald-300';
			case 'done':      return 'bg-gray-800/60 border-gray-700 text-gray-300';
			case 'error':     return 'bg-red-900/30 border-red-700/50 text-red-300';
			case 'cancelled': return 'bg-gray-800/60 border-gray-700 text-gray-500';
			default:          return 'bg-gray-800/60 border-gray-700 text-gray-400';
		}
	}
	function statusIcon(s: string) {
		switch (s) {
			case 'queued':    return '⏳';
			case 'running':   return '🦖';
			case 'done':      return '✅';
			case 'error':     return '❌';
			case 'cancelled': return '⏹';
			default:          return '•';
		}
	}
	function fmtTime(ms?: number) {
		if (!ms) return '';
		return new Date(ms).toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' });
	}
	async function onDownload(a: { name: string; url: string }) {
		const r = await downloadFile(a.url, a.name);
		if (r.success) toast.success(`다운로드 완료: ${a.name}`);
		else toast.error(`다운로드 실패: ${r.error || a.name}`);
	}
</script>

<div class="rounded-xl border p-3 space-y-2 {statusColor(task.status)}">
	<div class="flex items-start gap-2">
		<span class="text-lg flex-shrink-0">{statusIcon(task.status)}</span>
		<div class="flex-1 min-w-0">
			<p class="text-sm font-medium text-white truncate">{task.prompt}</p>
			<p class="text-[10px] text-gray-500">
				{fmtTime(task.createdAt)}
				{#if task.status === 'running'}
					· iter {task.iteration}/{task.maxIterations}
				{:else if task.status === 'done'}
					· {task.iteration} iter · 완료 {fmtTime(task.completedAt)}
				{/if}
			</p>
		</div>
		{#if (task.status === 'running' || task.status === 'queued') && onCancel}
			<button onclick={onCancel} class="text-xs text-gray-400 hover:text-red-400" aria-label="취소">⏹</button>
		{/if}
	</div>

	{#if task.progressMessages.length > 0 && task.status === 'running'}
		<div class="text-[11px] text-gray-400 max-h-16 overflow-y-auto pl-7 space-y-0.5">
			{#each task.progressMessages.slice(-4) as line}
				<div class="truncate">{line}</div>
			{/each}
		</div>
	{/if}

	{#if task.status === 'done' && task.summary}
		<div class="text-xs text-gray-300 whitespace-pre-wrap pl-7 max-h-32 overflow-y-auto">{task.summary}</div>
	{/if}

	{#if task.status === 'error' && task.error}
		<div class="text-xs text-red-400 pl-7">{task.error}</div>
	{/if}

	{#if task.artifacts.length > 0}
		<div class="pl-7 space-y-1 pt-1">
			{#each task.artifacts as a}
				<button
					onclick={() => onDownload(a)}
					class="flex items-center gap-2 w-full text-left px-2.5 py-1.5 rounded-lg bg-gray-700/40 hover:bg-gray-600/50 transition-colors text-xs"
				>
					<span>📥</span>
					<span class="flex-1 truncate">{a.name}</span>
				</button>
			{/each}
		</div>
	{/if}
</div>
