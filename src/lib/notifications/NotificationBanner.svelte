<script lang="ts">
	/**
	 * 포그라운드 알림 배너 — 상단에서 슬라이드 다운
	 */
	import type { NotificationMessage } from './websocket';

	interface Props {
		notification: NotificationMessage | null;
		onDismiss: () => void;
		onTap?: (action?: string) => void;
	}

	let { notification, onDismiss, onTap }: Props = $props();

	let visible = $state(false);
	let dismissTimer: ReturnType<typeof setTimeout> | null = null;

	// notification이 바뀌면 표시
	$effect(() => {
		if (notification) {
			visible = true;
			if (dismissTimer) clearTimeout(dismissTimer);
			dismissTimer = setTimeout(() => {
				visible = false;
				setTimeout(onDismiss, 300); // 애니메이션 후 제거
			}, 5000);
		}
	});

	function handleTap() {
		visible = false;
		if (onTap) onTap(notification?.action);
		setTimeout(onDismiss, 300);
	}
</script>

{#if notification}
	<!-- svelte-ignore a11y_click_events_have_key_events -->
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<div
		class="fixed top-0 left-0 right-0 z-50 px-4 pt-[env(safe-area-inset-top,12px)] transition-transform duration-300 ease-out"
		style="transform: translateY({visible ? '0' : '-100%'})"
		onclick={handleTap}
	>
		<div class="bg-gray-800 border border-gray-700 rounded-2xl px-4 py-3 shadow-2xl shadow-black/50 mx-auto max-w-lg">
			<div class="flex items-start gap-3">
				<span class="text-2xl flex-shrink-0 mt-0.5">🦖</span>
				<div class="flex-1 min-w-0">
					{#if notification.title}
						<p class="font-semibold text-white text-sm truncate">{notification.title}</p>
					{/if}
					<p class="text-gray-300 text-sm line-clamp-2">{notification.body}</p>
				</div>
				<button
					onclick={(e: MouseEvent) => { e.stopPropagation(); visible = false; setTimeout(onDismiss, 300); }}
					class="text-gray-500 hover:text-white flex-shrink-0 p-1"
				>
					✕
				</button>
			</div>
		</div>
	</div>
{/if}
