<script lang="ts">
	import { goto } from '$app/navigation';
	import { conversation } from '$lib/stores/conversation.svelte';
	import { WebSpeechSTT } from '$lib/stt/webspeech';
	import { WebSpeechTTS } from '$lib/tts/webspeech';
	import { onMount } from 'svelte';

	interface Message {
		role: 'user' | 'assistant';
		content: string;
	}

	let messages: Message[] = $state([]);
	let input = $state('');
	let isLoading = $state(false);
	let messagesContainer: HTMLDivElement;
	let showTextInput = $state(false);

	let stt: WebSpeechSTT | null = $state(null);
	let tts: WebSpeechTTS | null = $state(null);
	let waveformBars: number[] = $state(Array(24).fill(4));
	let animFrame = 0;

	function scrollToBottom() {
		if (messagesContainer) {
			requestAnimationFrame(() => {
				messagesContainer.scrollTop = messagesContainer.scrollHeight;
			});
		}
	}

	onMount(() => {
		// Initialize TTS
		tts = new WebSpeechTTS({
			onStart: () => conversation.setSpeaking(),
			onEnd: () => {
				if (conversation.micEnabled) {
					conversation.setListening();
					stt?.start();
				} else {
					conversation.setIdle();
				}
			},
			onSentence: () => {}
		});

		// Initialize STT
		stt = new WebSpeechSTT({
			onInterim: (text) => {
				conversation.interimText = text;
			},
			onFinal: (text) => {
				if (text.trim()) {
					conversation.interimText = '';
					sendMessage(text.trim());
				}
			},
			onError: (err) => {
				console.error('STT error:', err);
			},
			onEnd: () => {}
		});

		// Animate waveform
		const animate = () => {
			if (conversation.state === 'listening' || conversation.state === 'speaking') {
				waveformBars = waveformBars.map((_, i) => {
					const t = Date.now() / 200;
					const base = conversation.state === 'listening' ? 12 : 8;
					const amp = conversation.state === 'listening' ? 16 : 10;
					return base + Math.sin(t + i * 0.4) * amp * (0.5 + Math.random() * 0.5);
				});
			} else {
				waveformBars = waveformBars.map((_, i) => 3 + Math.sin(i * 0.5) * 2);
			}
			animFrame = requestAnimationFrame(animate);
		};
		animFrame = requestAnimationFrame(animate);

		return () => {
			cancelAnimationFrame(animFrame);
			stt?.stop();
			tts?.stop();
		};
	});

	function toggleMic() {
		conversation.micEnabled = !conversation.micEnabled;
		if (conversation.micEnabled) {
			conversation.setListening();
			stt?.start();
		} else {
			stt?.stop();
			tts?.stop();
			conversation.setIdle();
		}
	}

	async function sendMessage(text?: string) {
		const finalText = text || input.trim();
		if (!finalText || isLoading) return;

		// Barge-in: stop TTS if speaking
		if (conversation.state === 'speaking') {
			tts?.stop();
		}

		// Stop STT during processing
		stt?.stop();
		conversation.setProcessing();

		messages.push({ role: 'user', content: finalText });
		if (!text) input = '';
		isLoading = true;

		messages.push({ role: 'assistant', content: '' });
		const assistantIdx = messages.length - 1;
		scrollToBottom();

		let fullResponse = '';
		let sentenceBuffer = '';

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
							fullResponse += delta;
							messages[assistantIdx].content = fullResponse;
							scrollToBottom();

							// Stream TTS: accumulate and speak sentence by sentence
							if (conversation.micEnabled) {
								sentenceBuffer += delta;
								const sentenceEnd = sentenceBuffer.match(/[.!?。\n]/);
								if (sentenceEnd && sentenceBuffer.trim().length > 5) {
									tts?.addChunk(sentenceBuffer.trim());
									sentenceBuffer = '';
								}
							}
						}
					} catch {
						// skip
					}
				}
			}

			// Speak remaining buffer
			if (sentenceBuffer.trim() && conversation.micEnabled) {
				tts?.addChunk(sentenceBuffer.trim());
			}
		} catch (err) {
			messages[assistantIdx].content = `⚠️ 오류: ${err instanceof Error ? err.message : '알 수 없는 오류'}`;
		} finally {
			isLoading = false;

			// If mic not enabled or no TTS, go to idle
			if (!conversation.micEnabled) {
				conversation.setIdle();
			} else if (!tts?.isSpeaking) {
				// TTS didn't start (empty response), go back to listening
				conversation.setListening();
				stt?.start();
			}
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

<div class="flex flex-col h-screen bg-gray-950 text-white">
	<!-- Header -->
	<header class="flex items-center justify-between px-4 py-3 bg-gray-900 border-b border-gray-800">
		<div class="flex items-center gap-2">
			<span class="text-xl">🦖</span>
			<span class="font-semibold text-lg">렉스</span>
			<span
				class="text-xs px-2 py-0.5 rounded-full"
				style="background-color: {conversation.stateColor}20; color: {conversation.stateColor}"
			>
				{conversation.stateLabel}
			</span>
		</div>
		<div class="flex items-center gap-2">
			<button
				onclick={() => (showTextInput = !showTextInput)}
				class="p-2 rounded-lg hover:bg-gray-800 transition-colors text-sm"
				title="텍스트 입력 토글"
			>
				⌨️
			</button>
			<button onclick={() => goto('/settings')} class="p-2 rounded-lg hover:bg-gray-800 transition-colors">
				⚙️
			</button>
		</div>
	</header>

	<!-- Messages -->
	<div bind:this={messagesContainer} class="flex-1 overflow-y-auto px-4 py-4 space-y-4">
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
						? 'bg-blue-600 text-white rounded-br-md'
						: 'bg-gray-800 text-gray-100 rounded-bl-md'}"
				>
					{#if message.role === 'assistant' && !message.content && isLoading}
						<span class="inline-flex gap-1">
							<span class="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></span>
							<span
								class="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:0.1s]"
							></span>
							<span
								class="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:0.2s]"
							></span>
						</span>
					{:else}
						<p class="whitespace-pre-wrap">{message.content}</p>
					{/if}
				</div>
			</div>
		{/each}
	</div>

	<!-- Waveform + Interim -->
	<div class="px-4 py-2 space-y-2">
		<!-- Interim text (real-time subtitle) -->
		{#if conversation.interimText}
			<div class="text-center text-sm text-gray-400 italic truncate">
				"{conversation.interimText}"
			</div>
		{/if}

		<!-- Waveform visualization -->
		<div
			class="flex items-center justify-center h-16 rounded-xl border transition-colors duration-300"
			style="background-color: {conversation.stateColor}08; border-color: {conversation.stateColor}30"
		>
			<div class="flex items-end gap-[3px] h-10">
				{#each waveformBars as height}
					<div
						class="w-[3px] rounded-full transition-all duration-75"
						style="height: {height}px; background-color: {conversation.stateColor}"
					></div>
				{/each}
			</div>
		</div>

		<!-- Mic toggle button -->
		<div class="flex justify-center">
			<button
				onclick={toggleMic}
				class="w-16 h-16 rounded-full flex items-center justify-center text-2xl transition-all duration-300 {conversation.micEnabled
					? 'bg-red-600 hover:bg-red-500 shadow-lg shadow-red-600/30 scale-110'
					: 'bg-gray-700 hover:bg-gray-600'}"
			>
				{conversation.micEnabled ? '🎤' : '🎙️'}
			</button>
		</div>
	</div>

	<!-- Text input (toggle) -->
	{#if showTextInput}
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
					onclick={() => sendMessage()}
					disabled={!input.trim() || isLoading}
					class="px-4 py-3 bg-blue-600 text-white rounded-xl font-medium hover:bg-blue-500 disabled:opacity-50 transition-colors"
				>
					전송
				</button>
			</div>
		</div>
	{/if}
</div>
