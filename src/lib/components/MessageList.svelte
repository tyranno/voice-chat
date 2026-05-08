<script lang="ts">
	interface DownloadInfo {
		url: string;
		filename: string;
		status: 'idle' | 'downloading' | 'complete' | 'error';
		progress: number;
		error?: string;
	}
	interface Message {
		role: 'user' | 'assistant';
		content: string;
		downloads?: DownloadInfo[];
	}
	interface Props {
		messages: Message[];
		isLoading: boolean;
		container?: HTMLDivElement;
		onDownload: (dl: DownloadInfo) => void;
	}
	let { messages, isLoading, container = $bindable(), onDownload }: Props = $props();
</script>

<div bind:this={container} class="flex-1 overflow-y-auto px-4 py-4 space-y-4">
	{#if messages.length === 0}
		<div class="flex flex-col items-center justify-center h-full text-gray-500 gap-4">
			<span class="text-6xl">🦖</span>
			<p class="text-lg">마이크를 켜고 렉스에게 말해보세요!</p>
			<p class="text-sm text-gray-600">아래 마이크 버튼을 눌러 시작</p>
		</div>
	{/if}

	{#each messages as message}
		<div class="flex {message.role === 'user' ? 'justify-end' : 'justify-start'}">
			<div
				class="max-w-[80%] px-4 py-2.5 rounded-2xl {message.role === 'user'
					? 'bg-emerald-500 text-white rounded-br-md'
					: 'bg-gray-800 text-gray-100 rounded-bl-md'}"
			>
				{#if message.role === 'assistant' && !message.content && isLoading}
					<span class="inline-flex gap-1">
						<span class="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></span>
						<span class="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:0.1s]"></span>
						<span class="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:0.2s]"></span>
					</span>
				{:else}
					<p class="whitespace-pre-wrap">{message.content}</p>
					{#if message.downloads && message.downloads.length > 0}
						<div class="mt-2 space-y-1.5 border-t border-gray-700 pt-2">
							{#each message.downloads as dl}
								<button
									onclick={() => onDownload(dl)}
									disabled={dl.status === 'downloading'}
									class="flex items-center gap-2 w-full text-left px-3 py-2 rounded-lg bg-gray-700/50 hover:bg-gray-600/50 transition-colors text-sm disabled:opacity-70"
								>
									<span class="flex-shrink-0">
										{#if dl.status === 'complete'}✅
										{:else if dl.status === 'error'}❌
										{:else if dl.status === 'downloading'}⏳
										{:else}📥{/if}
									</span>
									<span class="flex-1 truncate">{dl.filename}</span>
									{#if dl.status === 'downloading'}
										<span class="text-xs text-blue-400">{dl.progress}%</span>
									{:else if dl.status === 'error'}
										<span class="text-xs text-red-400">{dl.error}</span>
									{/if}
								</button>
							{/each}
						</div>
					{/if}
				{/if}
			</div>
		</div>
	{/each}
</div>
