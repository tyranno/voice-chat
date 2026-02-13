<script lang="ts">
	import { goto } from '$app/navigation';
	import { conversation } from '$lib/stores/conversation.svelte';
	import { settings } from '$lib/stores/settings.svelte';
	import { streamChat } from '$lib/api/openclaw';
	import { checkServerHealth } from '$lib/api/health';
	import { getInstances, type Instance } from '$lib/api/instances';
	import { WebSpeechSTT } from '$lib/stt/webspeech';
	import { CapacitorSTT } from '$lib/stt/capacitor';
	import { Capacitor } from '@capacitor/core';
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

	// Connection state
	let appState = $state<'checking' | 'no-server' | 'select-instance' | 'no-instance' | 'connected'>('checking');
	let connectionError = $state('');
	let instances = $state<Instance[]>([]);

	let stt: WebSpeechSTT | CapacitorSTT | null = $state(null);
	let tts: WebSpeechTTS | null = $state(null);
	let waveformBars: number[] = $state(Array(24).fill(4));
	let animFrame = 0;
	let sttError = $state('');

	function scrollToBottom() {
		if (messagesContainer) {
			requestAnimationFrame(() => {
				messagesContainer.scrollTop = messagesContainer.scrollHeight;
			});
		}
	}

	async function checkConnection() {
		appState = 'checking';
		connectionError = '';

		if (!settings.isConfigured) {
			appState = 'no-server';
			connectionError = '서버 주소를 설정해주세요';
			return;
		}

		// 1. Health check
		const health = await checkServerHealth();
		if (!health.ok) {
			appState = 'no-server';
			connectionError = health.error || '서버 연결 실패';
			return;
		}

		// 2. Fetch instances
		try {
			instances = await getInstances();
		} catch (err) {
			appState = 'no-server';
			connectionError = `인스턴스 조회 실패: ${err instanceof Error ? err.message : ''}`;
			return;
		}

		if (instances.length === 0) {
			appState = 'no-instance';
			return;
		}

		// 3. Auto-select if saved instance still exists, or only 1 instance
		const savedExists = instances.find(i => i.id === settings.selectedInstance);
		if (savedExists) {
			appState = 'connected';
		} else if (instances.length === 1) {
			settings.selectedInstance = instances[0].id;
			appState = 'connected';
		} else {
			appState = 'select-instance';
		}
	}

	function selectInstance(id: string) {
		settings.selectedInstance = id;
		appState = 'connected';
	}

	onMount(async () => {
		await checkConnection();

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

		// Initialize STT based on platform
		const sttCallbacks = {
			onInterim: (text: string) => {
				conversation.interimText = text;
			},
			onFinal: (text: string) => {
				if (text.trim()) {
					conversation.interimText = '';
					sendMessage(text.trim());
				}
			},
			onError: (err: string) => {
				console.error('STT error:', err);
				sttError = err;
				// Don't setIdle here - let it show progress
			},
			onEnd: () => {}
		};

		if (Capacitor.isNativePlatform()) {
			stt = new CapacitorSTT(sttCallbacks);
		} else {
			stt = new WebSpeechSTT(sttCallbacks);
		}

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

	async function toggleMic() {
		conversation.micEnabled = !conversation.micEnabled;
		sttError = '';
		if (conversation.micEnabled) {
			conversation.setListening();
			try {
				await stt?.start();
			} catch (e) {
				sttError = `start() 에러: ${e}`;
				conversation.setIdle();
			}
		} else {
			stt?.stop();
			tts?.stop();
			conversation.setIdle();
		}
	}

	async function sendMessage(text?: string) {
		const finalText = text || input.trim();
		if (!finalText || isLoading) return;

		if (conversation.state === 'speaking') {
			tts?.stop();
		}

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
			await new Promise<void>((resolve, reject) => {
				streamChat(
					messages.slice(0, -1).map((m) => ({ role: m.role, content: m.content })),
					{
						onDelta: (delta) => {
							fullResponse += delta;
							messages[assistantIdx].content = fullResponse;
							scrollToBottom();

							if (conversation.micEnabled) {
								sentenceBuffer += delta;
								const sentenceEnd = sentenceBuffer.match(/[.!?。\n]/);
								if (sentenceEnd && sentenceBuffer.trim().length > 5) {
									tts?.addChunk(sentenceBuffer.trim());
									sentenceBuffer = '';
								}
							}
						},
						onDone: () => {
							if (sentenceBuffer.trim() && conversation.micEnabled) {
								tts?.addChunk(sentenceBuffer.trim());
							}
							resolve();
						},
						onError: (err) => reject(err)
					}
				);
			});
		} catch (err) {
			messages[assistantIdx].content = `⚠️ 오류: ${err instanceof Error ? err.message : '알 수 없는 오류'}`;
		} finally {
			isLoading = false;

			if (!conversation.micEnabled) {
				conversation.setIdle();
			} else if (!tts?.isSpeaking) {
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

{#if appState === 'checking'}
<!-- Splash / Connection Check -->
<div class="app-container bg-gray-950 text-white items-center justify-center gap-4">
	<span class="text-6xl animate-pulse">🦖</span>
	<p class="text-gray-400">서버 연결 중...</p>
</div>

{:else if appState === 'no-server'}
<!-- Server unreachable or not configured -->
<div class="app-container bg-gray-950 text-white items-center justify-center gap-6 px-8">
	<span class="text-6xl">🦖</span>
	<p class="text-xl font-semibold">서버에 연결할 수 없습니다</p>
	<p class="text-gray-400 text-center text-sm">{connectionError || settings.serverUrl}</p>
	<div class="flex gap-3">
		<button
			onclick={() => goto('/settings')}
			class="px-6 py-3 bg-blue-600 hover:bg-blue-500 rounded-xl font-medium transition-colors"
		>
			⚙️ 서버 설정
		</button>
		<button
			onclick={checkConnection}
			class="px-6 py-3 bg-gray-700 hover:bg-gray-600 rounded-xl font-medium transition-colors"
		>
			🔄 재시도
		</button>
	</div>
</div>

{:else if appState === 'no-instance'}
<!-- Server OK but no bridges connected -->
<div class="app-container bg-gray-950 text-white items-center justify-center gap-6 px-8">
	<span class="text-6xl">🦖</span>
	<p class="text-xl font-semibold">연결된 인스턴스 없음</p>
	<p class="text-gray-400 text-center text-sm">서버에 연결되었지만, OpenClaw 인스턴스가 없습니다.<br/>ClawBridge를 실행해주세요.</p>
	<div class="flex gap-3">
		<button
			onclick={checkConnection}
			class="px-6 py-3 bg-blue-600 hover:bg-blue-500 rounded-xl font-medium transition-colors"
		>
			🔄 새로고침
		</button>
		<button
			onclick={() => goto('/settings')}
			class="px-6 py-3 bg-gray-700 hover:bg-gray-600 rounded-xl font-medium transition-colors"
		>
			⚙️ 설정
		</button>
	</div>
</div>

{:else if appState === 'select-instance'}
<!-- Multiple instances available -->
<div class="app-container bg-gray-950 text-white">
	<header class="flex items-center gap-3 px-4 py-3 bg-gray-900 border-b border-gray-800">
		<span class="text-xl">🦖</span>
		<span class="font-semibold text-lg">인스턴스 선택</span>
	</header>
	<div class="flex-1 overflow-y-auto px-4 py-6 space-y-3">
		<p class="text-gray-400 text-sm mb-4">대화할 OpenClaw 인스턴스를 선택하세요</p>
		{#each instances as inst}
			<button
				onclick={() => selectInstance(inst.id)}
				class="w-full flex items-center gap-4 p-4 bg-gray-900 hover:bg-gray-800 rounded-xl transition-colors text-left"
			>
				<span class="text-3xl">🖥️</span>
				<div class="flex-1">
					<p class="font-medium text-white">{inst.name}</p>
					<p class="text-sm text-gray-400">{inst.status} · {new Date(inst.connectedAt).toLocaleString('ko-KR')}</p>
				</div>
				<span class="text-2xl text-gray-500">→</span>
			</button>
		{/each}
	</div>
	<div class="px-4 pb-6 flex gap-3">
		<button
			onclick={checkConnection}
			class="flex-1 px-4 py-3 bg-gray-700 hover:bg-gray-600 rounded-xl font-medium transition-colors"
		>
			🔄 새로고침
		</button>
		<button
			onclick={() => goto('/settings')}
			class="px-4 py-3 bg-gray-800 hover:bg-gray-700 rounded-xl transition-colors"
		>
			⚙️
		</button>
	</div>
</div>

{:else}
<!-- Connected — Chat UI -->
<div class="app-container bg-gray-950 text-white">
	<!-- Header -->
	<header class="flex-shrink-0 flex items-center justify-between px-4 py-3 bg-gray-900 border-b border-gray-800">
		<div class="flex items-center gap-2">
			<button
				onclick={() => { appState = 'select-instance'; }}
				class="text-xl hover:scale-110 transition-transform"
				title="인스턴스 변경"
			>🦖</button>
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

	<!-- Waveform + Interim -->
	<div class="px-4 py-2 space-y-2">
		{#if sttError}
			<div class="text-center text-sm text-red-400 bg-red-900/30 rounded-lg px-3 py-2">
				⚠️ {sttError}
				<button onclick={() => sttError = ''} class="ml-2 text-red-300 hover:text-white">✕</button>
			</div>
		{/if}
		
		{#if conversation.interimText}
			<div class="text-center text-sm text-gray-400 italic truncate">
				"{conversation.interimText}"
			</div>
		{/if}

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

		<div class="flex justify-center pb-4">
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
{/if}
