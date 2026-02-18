<script lang="ts">
	import { goto } from '$app/navigation';
	import { getNotifications, clearAll } from '$lib/stores/notifications.svelte';

	const typeIcons: Record<string, string> = {
		info: 'ℹ️',
		success: '✅',
		warning: '⚠️',
		error: '❌'
	};

	let notifications = $derived(getNotifications());

	function formatTime(ts: number): string {
		const d = new Date(ts);
		const now = new Date();
		const diff = now.getTime() - d.getTime();

		if (diff < 60000) return '방금 전';
		if (diff < 3600000) return `${Math.floor(diff / 60000)}분 전`;
		if (diff < 86400000) return `${Math.floor(diff / 3600000)}시간 전`;

		return d.toLocaleDateString('ko-KR', {
			month: 'short',
			day: 'numeric',
			hour: '2-digit',
			minute: '2-digit'
		});
	}
</script>

<div class="app-container bg-gray-950 text-white">
	<!-- Header -->
	<header class="flex-shrink-0 flex items-center gap-3 px-4 py-3 bg-gray-900 border-b border-gray-800">
		<button
			onclick={() => goto('/')}
			class="p-2 rounded-lg hover:bg-gray-800 transition-colors"
		>←</button>
		<span class="font-semibold text-lg flex-1">🔔 알림</span>
		{#if notifications.length > 0}
			<button
				onclick={clearAll}
				class="px-3 py-1.5 text-xs bg-gray-700 hover:bg-gray-600 rounded-lg transition-colors"
			>모두 삭제</button>
		{/if}
	</header>

	<!-- List -->
	<div class="flex-1 overflow-y-auto">
		{#if notifications.length === 0}
			<div class="flex flex-col items-center justify-center h-full text-gray-500 gap-4">
				<span class="text-5xl">🔔</span>
				<p class="text-lg">알림이 없습니다</p>
			</div>
		{:else}
			{#each notifications as notif}
				<div class="px-4 py-3 border-b border-gray-800/50 hover:bg-gray-900/50 transition-colors">
					<div class="flex items-start gap-3">
						<span class="text-xl mt-0.5">{typeIcons[notif.type] || 'ℹ️'}</span>
						<div class="flex-1 min-w-0">
							{#if notif.title}
								<p class="font-medium text-sm">{notif.title}</p>
							{/if}
							<p class="text-sm text-gray-300 mt-0.5">{notif.message}</p>
							<p class="text-xs text-gray-500 mt-1">{formatTime(notif.timestamp)}</p>
						</div>
					</div>
				</div>
			{/each}
		{/if}
	</div>
</div>
