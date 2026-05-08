<script lang="ts">
	interface Props {
		show: boolean;
		onCancel: () => void;
		onConfirm: () => void;
	}
	let { show, onCancel, onConfirm }: Props = $props();
</script>

{#if show}
	<div class="fixed inset-0 z-[100] flex items-center justify-center bg-black/70">
		<div class="bg-gray-900 rounded-2xl p-6 mx-8 max-w-sm w-full shadow-2xl">
			<p class="text-white text-lg font-semibold text-center mb-2">앱 종료</p>
			<p class="text-gray-400 text-center text-sm mb-6">앱을 종료하시겠습니까?</p>
			<div class="flex gap-3">
				<button
					onclick={onCancel}
					class="flex-1 px-4 py-2.5 bg-gray-700 hover:bg-gray-600 rounded-xl font-medium text-white transition-colors"
				>취소</button>
				<button
					onclick={onConfirm}
					class="flex-1 px-4 py-2.5 bg-red-600 hover:bg-red-500 rounded-xl font-medium text-white transition-colors"
				>종료</button>
			</div>
		</div>
	</div>
{/if}
