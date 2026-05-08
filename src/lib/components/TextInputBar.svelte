<script lang="ts">
	interface Props {
		show: boolean;
		isLoading: boolean;
		value: string;
		onSend: () => void;
		onKeydown: (e: KeyboardEvent) => void;
	}
	let { show, isLoading, value = $bindable(), onSend, onKeydown }: Props = $props();
</script>

{#if show}
	<div class="flex-shrink-0 px-4 pb-4 pt-2">
		<div class="flex gap-2">
			<input
				type="text"
				bind:value
				onkeydown={onKeydown}
				placeholder={isLoading ? '응답 중... (전송하면 대기열에 추가)' : '메시지를 입력하세요...'}
				class="flex-1 px-4 py-3 bg-gray-800 border border-gray-700 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-emerald-500"
			/>
			<button
				onclick={onSend}
				disabled={!value.trim()}
				class="px-4 py-3 bg-emerald-500 text-white rounded-xl font-medium hover:bg-emerald-400 disabled:opacity-50 transition-colors"
			>
				{isLoading ? '대기' : '전송'}
			</button>
		</div>
	</div>
{/if}
