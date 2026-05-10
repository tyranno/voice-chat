<script lang="ts">
	interface ConversationLike {
		stateColor: string;
		stateLabel: string;
	}
	interface Props {
		instanceLabel: string;
		conversation: ConversationLike;
		showDropdown: boolean;
		activeTaskCount?: number;
		onToggleSidebar: () => void;
		onChangeInstance: () => void;
		onToggleTextInput: () => void;
		onOpenSettings: () => void;
		onToggleDropdown: () => void;
		onCloseDropdown: () => void;
		onNewConversation: () => void;
		onOpenNotifications: () => void;
		onOpenMusic: () => void;
		onOpenTasks: () => void;
	}
	let {
		instanceLabel, conversation, showDropdown, activeTaskCount = 0,
		onToggleSidebar, onChangeInstance, onToggleTextInput, onOpenSettings,
		onToggleDropdown, onCloseDropdown,
		onNewConversation, onOpenNotifications, onOpenMusic, onOpenTasks
	}: Props = $props();
</script>

<header
	class="flex-shrink-0 flex items-center justify-between px-3 py-2 bg-gray-900 border-b border-gray-800"
	style="padding-top: env(safe-area-inset-top);"
>
	<div class="flex items-center gap-1.5">
		<button
			onclick={onToggleSidebar}
			class="p-1.5 rounded-lg hover:bg-gray-800 transition-colors text-sm"
			title="대화 목록"
		>☰</button>
		<button
			onclick={onChangeInstance}
			class="flex items-center gap-1 px-1.5 py-0.5 rounded-lg hover:bg-gray-800 transition-colors"
			title="컴퓨터 변경"
		>
			<span class="text-lg">🦖</span>
			<span class="font-medium text-sm">{instanceLabel}</span>
		</button>
		<span
			class="text-[10px] px-1.5 py-0.5 rounded-full"
			style="background-color: {conversation.stateColor}20; color: {conversation.stateColor}"
		>
			{conversation.stateLabel}
		</span>
	</div>
	<div class="flex items-center gap-1">
		<button
			onclick={onToggleTextInput}
			class="p-1.5 rounded-lg hover:bg-gray-800 transition-colors text-sm"
			title="텍스트 입력"
		>⌨️</button>
		<button
			onclick={onOpenSettings}
			class="p-1.5 rounded-lg hover:bg-gray-800 transition-colors text-sm"
			title="설정"
		>⚙️</button>
		<div class="relative">
			<button
				onclick={onToggleDropdown}
				class="p-1.5 rounded-lg hover:bg-gray-800 transition-colors text-sm"
				title="메뉴"
			>⋯</button>
			{#if showDropdown}
				<div class="fixed inset-0 z-40" onclick={onCloseDropdown}></div>
				<div class="absolute right-0 top-full mt-1 z-50 w-44 bg-gray-800 border border-gray-700 rounded-xl shadow-2xl overflow-hidden">
					<button onclick={() => { onCloseDropdown(); onNewConversation(); }} class="w-full text-left px-3 py-2.5 hover:bg-gray-700 transition-colors text-sm flex items-center gap-2">
						<span>✏️</span><span>새 대화</span>
					</button>
					<button onclick={() => { onCloseDropdown(); onOpenTasks(); }} class="w-full text-left px-3 py-2.5 hover:bg-gray-700 transition-colors text-sm flex items-center gap-2">
						<span>🦖</span><span>AI 작업</span>
						{#if activeTaskCount > 0}
							<span class="ml-auto text-[10px] px-1.5 py-0.5 bg-emerald-500/30 text-emerald-300 rounded-full">{activeTaskCount}</span>
						{/if}
					</button>
					<button onclick={() => { onCloseDropdown(); onOpenNotifications(); }} class="w-full text-left px-3 py-2.5 hover:bg-gray-700 transition-colors text-sm flex items-center gap-2">
						<span>🔔</span><span>알림</span>
					</button>
					<button onclick={() => { onCloseDropdown(); onOpenMusic(); }} class="w-full text-left px-3 py-2.5 hover:bg-gray-700 transition-colors text-sm flex items-center gap-2">
						<span>🎵</span><span>음악</span>
					</button>
				</div>
			{/if}
		</div>
	</div>
</header>
