<script lang="ts">
	import type { ConversationMeta } from '$lib/api/conversations';

	interface Props {
		show: boolean;
		conversationList: ConversationMeta[];
		currentConversationId: string | null;
		onClose: () => void;
		onSwitch: (id: string) => void;
		onNew: () => void;
		onDelete: (id: string, e: Event) => void;
	}
	let { show, conversationList, currentConversationId, onClose, onSwitch, onNew, onDelete }: Props = $props();
</script>

{#if show}
	<div class="fixed inset-0 z-50 flex">
		<div class="absolute inset-0 bg-black/60" onclick={onClose}></div>
		<div class="relative w-72 max-w-[80vw] bg-gray-900 h-full flex flex-col shadow-2xl" style="padding-top: env(safe-area-inset-top);">
			<div class="flex items-center justify-between px-4 py-3 border-b border-gray-800">
				<span class="font-semibold text-lg">💬 대화 목록</span>
				<button
					onclick={onNew}
					class="px-3 py-1.5 bg-emerald-500 hover:bg-emerald-400 rounded-lg text-sm font-medium transition-colors"
				>+ 새 대화</button>
			</div>
			<div class="flex-1 overflow-y-auto">
				{#each conversationList as conv}
					<div
						role="button" tabindex="0"
						onclick={() => onSwitch(conv.id)}
						onkeydown={(e) => { if (e.key === 'Enter') onSwitch(conv.id); }}
						class="w-full text-left px-4 py-3 border-b border-gray-800/50 hover:bg-gray-800 transition-colors group cursor-pointer
							{conv.id === currentConversationId ? 'bg-gray-800/70' : ''}"
					>
						<div class="flex items-start justify-between gap-2">
							<div class="flex-1 min-w-0">
								<p class="text-sm font-medium truncate">{conv.title}</p>
								<p class="text-xs text-gray-500 mt-0.5">
									{new Date(conv.updatedAt).toLocaleDateString('ko-KR')} {new Date(conv.updatedAt).toLocaleTimeString('ko-KR', {hour: '2-digit', minute: '2-digit'})}
									· {conv.messageCount}개
								</p>
							</div>
							<span
								role="button" tabindex="-1"
								onclick={(e) => onDelete(conv.id, e)}
								onkeydown={(e) => { if (e.key === 'Enter') onDelete(conv.id, e); }}
								class="opacity-0 group-hover:opacity-100 p-1 text-gray-500 hover:text-red-400 transition-all cursor-pointer"
								title="삭제"
							>🗑</span>
						</div>
					</div>
				{/each}
				{#if conversationList.length === 0}
					<div class="px-4 py-8 text-center text-gray-500 text-sm">대화 내역이 없습니다</div>
				{/if}
			</div>
		</div>
	</div>
{/if}
