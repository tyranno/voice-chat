<script lang="ts">
	import { goto } from '$app/navigation';

	interface Message {
		role: 'user' | 'assistant';
		content: string;
	}

	let messages: Message[] = $state([]);
	let input = $state('');
	let isLoading = $state(false);
	let messagesContainer: HTMLDivElement;

	function scrollToBottom() {
		if (messagesContainer) {
			messagesContainer.scrollTop = messagesContainer.scrollHeight;
		}
	}

	async function sendMessage() {
		const text = input.trim();
		if (!text || isLoading) return;

		messages.push({ role: 'user', content: text });
		input = '';
		isLoading = true;

		// Add empty assistant message for streaming
		messages.push({ role: 'assistant', content: '' });
		const assistantIdx = messages.length - 1;

		try {
			const response = await fetch('/api/chat', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					messages: messages.slice(0, -1).map((m) => ({ role: m.role, content: m.content }))
				})
			});

			if (!response.ok) throw new Error(`HTTP ${response.status}`);
			if (!response.body) throw new Error('No response body');

			const reader = response.body.getReader();
			const decoder = new TextDecoder();
			let buffer = '';

			while (true) {
				const { done, value } = await reader.read();
				if (done) break;

				buffer += decoder.decode(value, { stream: true });
				const lines = buffer.split('\n');
				buffer = lines.pop() || '';

				for (const line of lines) {
					if (!line.startsWith('data: ')) continue;
					const data = line.slice(6);
					if (data === '[DONE]') break;

					try {
						const parsed = JSON.parse(data);
						const delta = parsed.choices?.[0]?.delta?.content;
						if (delta) {
							messages[assistantIdx].content += delta;
							scrollToBottom();
						}
					} catch {
						// skip parse errors
					}
				}
			}
		} catch (err) {
			messages[assistantIdx].content = `⚠️ 오류: ${err instanceof Error ? err.message : '알 수 없는 오류'}`;
		} finally {
			isLoading = false;
			scrollToBottom();
		}
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter' && !e.shiftKey) {
			e.preventDefault();
			sendMessage();
		}
	}
</script>

<div class="flex flex-col h-screen">
	<!-- Header -->
	<header class="flex items-center justify-between px-4 py-3 bg-gray-900 border-b border-gray-800">
		<div class="flex items-center gap-2">
			<span class="text-xl">🦖</span>
			<span class="font-semibold text-lg">렉스</span>
		</div>
		<button onclick={() => goto('/settings')} class="p-2 rounded-lg hover:bg-gray-800 transition-colors">
			⚙️
		</button>
	</header>

	<!-- Messages -->
	<div bind:this={messagesContainer} class="flex-1 overflow-y-auto px-4 py-4 space-y-4">
		{#if messages.length === 0}
			<div class="flex items-center justify-center h-full text-gray-500">
				<p>🦖 렉스에게 말해보세요!</p>
			</div>
		{/if}

		{#each messages as message}
			<div class="flex {message.role === 'user' ? 'justify-end' : 'justify-start'}">
				<div
					class="max-w-[80%] px-4 py-2.5 rounded-2xl {message.role === 'user'
						? 'bg-blue-600 text-white rounded-br-md'
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
					{/if}
				</div>
			</div>
		{/each}
	</div>

	<!-- Waveform Placeholder -->
	<div class="px-4 py-2">
		<div class="flex items-center justify-center h-12 rounded-xl bg-gray-900 border border-gray-800">
			<div class="flex items-end gap-0.5 h-6">
				{#each Array(20) as _, i}
					<div
						class="w-1 bg-gray-600 rounded-full"
						style="height: {4 + Math.sin(i * 0.5) * 8}px"
					></div>
				{/each}
			</div>
			<span class="ml-3 text-xs text-gray-500">🎤 음성 (Phase 3)</span>
		</div>
	</div>

	<!-- Input -->
	<div class="px-4 pb-4 pt-2">
		<div class="flex gap-2">
			<input
				type="text"
				bind:value={input}
				onkeydown={handleKeydown}
				placeholder="메시지를 입력하세요..."
				disabled={isLoading}
				class="flex-1 px-4 py-3 bg-gray-800 border border-gray-700 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 disabled:opacity-50"
			/>
			<button
				onclick={sendMessage}
				disabled={!input.trim() || isLoading}
				class="px-4 py-3 bg-blue-600 text-white rounded-xl font-medium hover:bg-blue-500 disabled:opacity-50 disabled:hover:bg-blue-600 transition-colors"
			>
				전송
			</button>
		</div>
	</div>
</div>
