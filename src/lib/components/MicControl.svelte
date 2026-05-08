<script lang="ts">
	interface ConversationLike {
		stateColor: string;
		interimText?: string;
		micEnabled: boolean;
	}
	interface Props {
		waveformBars: number[];
		conversation: ConversationLike;
		sttError: string;
		onToggleMic: () => void;
		onClearError: () => void;
	}
	let { waveformBars, conversation, sttError, onToggleMic, onClearError }: Props = $props();
</script>

<div class="flex-shrink-0 px-4 py-2 space-y-1 bg-gray-950" style="padding-bottom: env(safe-area-inset-bottom);">
	{#if sttError}
		<div class="text-center text-xs text-red-400 bg-red-900/30 rounded-lg px-2 py-1.5">
			⚠️ {sttError}
			<button onclick={onClearError} class="ml-1 text-red-300 hover:text-white">✕</button>
		</div>
	{/if}

	{#if conversation.interimText}
		<div class="text-center text-xs text-gray-400 italic truncate px-2">
			"{conversation.interimText}"
		</div>
	{/if}

	<div
		class="flex items-center justify-center h-12 rounded-xl border transition-colors duration-300"
		style="background-color: {conversation.stateColor}08; border-color: {conversation.stateColor}30"
	>
		<div class="flex items-end gap-[3px] h-8">
			{#each waveformBars as height}
				<div
					class="w-[2px] rounded-full transition-all duration-75"
					style="height: {Math.min(height, 28)}px; background-color: {conversation.stateColor}"
				></div>
			{/each}
		</div>
	</div>

	<div class="flex justify-center pb-2">
		<button
			onclick={onToggleMic}
			class="w-14 h-14 rounded-full flex items-center justify-center text-xl transition-all duration-300 {conversation.micEnabled
				? 'bg-red-600 hover:bg-red-500 shadow-lg shadow-red-600/30 scale-110'
				: 'bg-gray-700 hover:bg-gray-600'}"
		>
			{conversation.micEnabled ? '🎤' : '🎙️'}
		</button>
	</div>
</div>
