<script lang="ts">
	import { toast, type ToastKind } from '$lib/stores/toast.svelte';

	function bgClass(k: ToastKind) {
		switch (k) {
			case 'success': return 'bg-emerald-600 border-emerald-500';
			case 'warning': return 'bg-amber-600 border-amber-500';
			case 'error':   return 'bg-red-600 border-red-500';
			case 'info':
			default:        return 'bg-gray-800 border-gray-700';
		}
	}
	function icon(k: ToastKind) {
		switch (k) {
			case 'success': return '✅';
			case 'warning': return '⚠️';
			case 'error':   return '❌';
			default:        return 'ℹ️';
		}
	}
</script>

{#if toast.toasts.length > 0}
	<div
		class="fixed top-0 left-0 right-0 z-[200] pointer-events-none flex flex-col items-center gap-2 px-4"
		style="padding-top: max(0.5rem, env(safe-area-inset-top));"
	>
		{#each toast.toasts as t (t.id)}
			<div
				role="status"
				class="pointer-events-auto max-w-sm w-full px-4 py-2.5 rounded-xl shadow-2xl border text-white text-sm flex items-center gap-2 {bgClass(t.kind)}"
			>
				<span class="flex-shrink-0">{icon(t.kind)}</span>
				<span class="flex-1">{t.message}</span>
				<button
					onclick={() => toast.dismiss(t.id)}
					class="flex-shrink-0 text-white/70 hover:text-white px-1"
					aria-label="닫기"
				>✕</button>
			</div>
		{/each}
	</div>
{/if}
