<script lang="ts">
	import { goto } from '$app/navigation';
	import { conversation } from '$lib/stores/conversation.svelte';
	import { settings } from '$lib/stores/settings.svelte';
	import { streamChat } from '$lib/api/openclaw';
	import { checkServerHealth } from '$lib/api/health';
	import { getInstances, type Instance } from '$lib/api/instances';
	import { WebSpeechSTT } from '$lib/stt/webspeech';
	import { NativeSTT } from '$lib/stt/native';
	import { Capacitor } from '@capacitor/core';
	import { WebSpeechTTS } from '$lib/tts/webspeech';
	import { CapacitorTTS } from '$lib/tts/capacitor';
	import { CloudTTS } from '$lib/tts/cloud';
	import { onMount } from 'svelte';
	import { extractFileUrls, downloadFile } from '$lib/api/downloader';
	// SpeechRecognition imported dynamically in checkConnection to avoid SSR issues

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

	let messages: Message[] = $state([]);
	let input = $state('');
	let isLoading = $state(false);
	let messagesContainer: HTMLDivElement;
	let showTextInput = $state(false);

	// Connection state
	let appState = $state<'checking' | 'no-server' | 'select-instance' | 'no-instance' | 'connected'>('checking');
	let connectionError = $state('');
	let instances = $state<Instance[]>([]);

	let stt: WebSpeechSTT | NativeSTT | null = $state(null);
	let tts: WebSpeechTTS | CapacitorTTS | CloudTTS | null = $state(null);
	let waveformBars: number[] = $state(Array(24).fill(4));
	let animFrame = 0;
	let sttError = $state('');
	let debugLog = $state('');
	let finalBuffer = '';
	let finalTimer: ReturnType<typeof setTimeout> | null = null;
	const FINAL_DEBOUNCE_MS = 200;

	let pendingMessage = '';

	function flushFinalBuffer() {
		if (finalBuffer.trim()) {
			const text = finalBuffer.trim();
			finalBuffer = '';
			conversation.interimText = '';

			// Barge-in: TTS 재생 중이면 즉시 중지 + STT 재개
			if (tts && (tts as any)._speaking) {
				addDebug(`🔇 Barge-in: TTS 중지, 새 명령: "${text}"`);
				tts.stop();
				// stop()이 onEnd 콜백을 호출하여 STT resume됨
			}

			if (isLoading) {
				pendingMessage = text;
				addDebug(`📋 큐잉: "${text}" (응답 대기 중)`);
				return;
			}
			sendMessage(text);
		}
	}

	function addDebug(msg: string) {
		const t = new Date().toLocaleTimeString('ko-KR');
		debugLog = `[${t}] ${msg}\n${debugLog}`.slice(0, 2000);
		console.log(`[VoiceChat] ${msg}`);
	}

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
		addDebug(`서버 확인 시작: ${settings.serverUrl}`);

		if (!settings.isConfigured) {
			appState = 'no-server';
			connectionError = '서버 주소를 설정해주세요';
			addDebug('서버 URL 미설정');
			return;
		}

		// 1. Health check
		const health = await checkServerHealth();
		addDebug(`Health: ok=${health.ok}, ${health.latencyMs}ms, instances=${health.instances}, error=${health.error || 'none'}`);
		if (!health.ok) {
			appState = 'no-server';
			connectionError = health.error || '서버 연결 실패';
			return;
		}

		// 2. Fetch instances
		try {
			instances = await getInstances();
			addDebug(`인스턴스 ${instances.length}개: ${instances.map(i => i.name).join(', ')}`);
		} catch (err) {
			appState = 'no-server';
			connectionError = `인스턴스 조회 실패: ${err instanceof Error ? err.message : ''}`;
			addDebug(`인스턴스 조회 실패: ${err}`);
			return;
		}

		if (instances.length === 0) {
			appState = 'no-instance';
			addDebug('연결된 인스턴스 없음');
			return;
		}

		// 3. Show instance list — always let user pick (or confirm)
		const savedExists = instances.find(i => i.id === settings.selectedInstance);
		if (savedExists) {
			appState = 'connected';
		} else {
			appState = 'select-instance';
		}
		addDebug(`상태: ${appState}, 선택: ${settings.selectedInstance}`);
	}

	function selectInstance(id: string) {
		settings.selectedInstance = id;
		appState = 'connected';
		// 인스턴스 선택 즉시 마이크 자동 ON
		if (stt && Capacitor.isNativePlatform()) {
			conversation.micEnabled = true;
			conversation.setListening();
			addDebug('[VoiceChat] 마이크 자동 시작');
			stt.start().catch((e: any) => console.warn('[VoiceChat] Auto-mic failed:', e));
		}
	}

	onMount(async () => {
		try {
		addDebug(`Platform: ${Capacitor.getPlatform()}`);
		await checkConnection();

		// Initialize TTS — Cloud TTS on Android, WebSpeech on desktop
		const ttsCallbacks = {
			onStart: () => {
				conversation.setSpeaking();
				// 에코 방지: TTS 재생 중 STT 일시정지
				if (stt instanceof NativeSTT) {
					addDebug('🔇 TTS 시작 → STT 일시정지 (에코 방지)');
					stt.pause();
				}
			},
			onEnd: () => {
				// TTS 끝나면 STT 재개
				if (stt instanceof NativeSTT && conversation.micEnabled) {
					addDebug('🔊 TTS 끝 → STT 재개');
					stt.resume();
				}
				if (conversation.micEnabled) {
					conversation.setListening();
				} else {
					conversation.setIdle();
				}
			},
			onSentence: () => {}
		};

		if (Capacitor.isNativePlatform()) {
			tts = new CloudTTS(ttsCallbacks, settings.serverUrl);
			addDebug('TTS: Cloud TTS (Google Neural2)');
		} else {
			tts = new WebSpeechTTS(ttsCallbacks);
			addDebug(`TTS: WebSpeech (available: ${(tts as WebSpeechTTS).available})`);
		}

		// Initialize STT based on platform
		const sttCallbacks = {
			onInterim: (text: string) => {
				conversation.interimText = finalBuffer ? finalBuffer + ' ' + text : text;
			},
			onFinal: (text: string) => {
				if (text.trim()) {
					finalBuffer += (finalBuffer ? ' ' : '') + text.trim();
					conversation.interimText = finalBuffer;
					if (finalTimer) clearTimeout(finalTimer);
					finalTimer = setTimeout(flushFinalBuffer, FINAL_DEBOUNCE_MS);
				}
			},
			onError: (err: string) => {
				console.error('STT error:', err);
				sttError = err;
				// Don't setIdle here - let it show progress
			},
			onEnd: () => {
				// NativeSTT는 자체 auto-restart — WebSpeech만 여기서 재시작
				if (conversation.micEnabled && !isLoading && stt instanceof WebSpeechSTT) {
					addDebug('STT onEnd — 자동 재시작 (WebSpeech)');
					setTimeout(() => {
						if (conversation.micEnabled && !isLoading) {
							stt?.start();
						}
					}, 300);
				}
			}
		};

		if (Capacitor.isNativePlatform()) {
			stt = new NativeSTT(sttCallbacks, settings.serverUrl);
			addDebug('STT: Server STT (WebSocket → Vosk)');
		} else {
			stt = new WebSpeechSTT(sttCallbacks);
		}

		// Mic guardian — ensure STT is always running when mic is on
		// 더 보수적인 접근: 빈도 줄이고, 더 많은 상황에서 간섭하지 않음
		const micGuardian = setInterval(() => {
			if (!conversation.micEnabled || isLoading) return;
			if (conversation.state === 'speaking' || conversation.state === 'processing') return;
			
			// NativeSTT 특별 처리: 자체 재시작 관리 중이면 절대 간섭하지 않음
			if (stt instanceof NativeSTT) {
				if (stt.isPaused || stt.isStarting || stt.isListening || stt.isSessionActive || stt.isRestartPending) return;
			} else if (stt && stt.isListening) {
				return;
			}

			// 상태가 listening이 아니면 먼저 상태 수정
			if (conversation.state !== 'listening') {
				conversation.setListening();
			}
			
			// STT가 실제로 죽어있을 때만 재시작
			if (stt && !stt.isListening) {
				addDebug('[Guardian] STT dead — restarting');
				stt.start().catch((e) => {
					console.warn('[Guardian] Restart failed:', e);
				});
			}
		}, 5000);  // 3초 → 5초로 변경 (더 보수적)

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

		// 연결 완료 시 자동으로 마이크 ON (네이티브 앱만)
		if (appState === 'connected' && stt && Capacitor.isNativePlatform()) {
			conversation.micEnabled = true;
			conversation.setListening();
			addDebug('[VoiceChat] 마이크 자동 시작');
			try {
				await stt.start();
			} catch (e) {
				console.warn('[VoiceChat] Auto-mic failed:', e);
			}
		}

		return () => {
			console.log('[VoiceChat] Cleanup');
			cancelAnimationFrame(animFrame);
			clearInterval(micGuardian);
			if (stt instanceof NativeSTT) {
				stt.destroy();  // 완전한 정리
			} else {
				stt?.stop();
			}
			tts?.stop();
		};
		} catch (e) {
			addDebug(`onMount 에러: ${e}`);
			appState = 'no-server';
			connectionError = `초기화 에러: ${e}`;
		}
	});

	function playBeep(freq: number, duration: number) {
		try {
			const ctx = new AudioContext();
			const osc = ctx.createOscillator();
			const gain = ctx.createGain();
			osc.frequency.value = freq;
			gain.gain.value = 0.3;
			osc.connect(gain);
			gain.connect(ctx.destination);
			osc.start();
			gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + duration / 1000);
			osc.stop(ctx.currentTime + duration / 1000);
		} catch {}
	}

	async function toggleMic() {
		conversation.micEnabled = !conversation.micEnabled;
		sttError = '';

		// 진동 없음 — 시각적 피드백만

		if (conversation.micEnabled) {
			conversation.setListening();
			try {
				await stt?.start();
			} catch (e) {
				sttError = `start() 에러: ${e}`;
				conversation.setIdle();
			}
		} else {
			// finalBuffer 정리 — 의도치 않은 메시지 전송 방지
			if (finalTimer) { clearTimeout(finalTimer); finalTimer = null; }
			finalBuffer = '';
			conversation.interimText = '';
			stt?.stop();
			tts?.stop();
			conversation.setIdle();
		}
	}

	async function sendMessage(text?: string) {
		const finalText = text || input.trim();
		if (!finalText || isLoading) {
			addDebug(`sendMessage 스킵: text="${text}" isLoading=${isLoading}`);
			return;
		}
		addDebug(`📤 sendMessage: "${finalText}"`);

		// Track input method: voice (text param) vs keyboard (no text param)
		const isVoiceInput = !!text;

		if (conversation.state === 'speaking') {
			tts?.stop();
		}

		// STT pause는 TTS onStart에서만 처리 — 여기서는 하지 않음
		// 중복 pause 호출 방지 (TTS onStart에서 이미 pause됨)
		conversation.setProcessing();

		messages.push({ role: 'user', content: finalText });
		if (!isVoiceInput) input = '';
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
							if (fullResponse.length <= 30) addDebug(`📥 delta: "${delta}"`);

							// TTS: 문장 단위로 즉시 재생 (쉼표도 끊기)
							sentenceBuffer += delta;
							const sentenceEnd = sentenceBuffer.match(/[.!?,。\n]/);
							if (sentenceEnd && sentenceBuffer.trim().length > 3) {
								tts?.addChunk(sentenceBuffer.trim());
								sentenceBuffer = '';
							}
						},
						onDone: () => {
							addDebug(`✅ 응답완료: ${fullResponse.length}자`);
							if (sentenceBuffer.trim()) {
								addDebug(`🔊 TTS: "${sentenceBuffer.trim().substring(0, 30)}"`);
								tts?.addChunk(sentenceBuffer.trim());
							}
							// Extract file URLs for download buttons
							const fileUrls = extractFileUrls(fullResponse);
							if (fileUrls.length > 0) {
								messages[assistantIdx].downloads = fileUrls.map(f => ({
									...f,
									status: 'idle' as const,
									progress: 0
								}));
							}
							resolve();
						},
						onError: (err) => { addDebug(`❌ API에러: ${err}`); reject(err); }
					}
				);
			});
		} catch (err) {
			messages[assistantIdx].content = `⚠️ 오류: ${err instanceof Error ? err.message : '알 수 없는 오류'}`;
		} finally {
			isLoading = false;

			// Vosk는 항상 듣고 있으므로 resume 불필요
			// TTS가 끝나면 onEnd 콜백에서 상태 변경
			if (!conversation.micEnabled) {
				conversation.setIdle();
			} else if (!tts || !(tts as any)._speaking) {
				conversation.setListening();
			}

			// 대기 중인 메시지 전송
			if (pendingMessage) {
				const queued = pendingMessage;
				pendingMessage = '';
				addDebug(`📋 큐잉된 메시지 전송: "${queued}"`);
				setTimeout(() => sendMessage(queued), 200);
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

	async function handleDownload(dl: DownloadInfo) {
		if (dl.status === 'downloading') return;
		dl.status = 'downloading';
		dl.progress = 0;

		const result = await downloadFile(dl.url, dl.filename, (percent) => {
			dl.progress = percent;
		});

		if (result.success) {
			dl.status = 'complete';
			dl.progress = 100;
		} else {
			dl.status = 'error';
			dl.error = result.error || 'Download failed';
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
	{#if debugLog}
		<pre class="mt-4 text-xs text-gray-500 bg-gray-900 rounded-lg p-3 max-w-sm overflow-auto max-h-40 text-left">{debugLog}</pre>
	{/if}
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
<!-- Instance list with name editing -->
<div class="app-container bg-gray-950 text-white">
	<header class="flex items-center gap-3 px-4 py-3 bg-gray-900 border-b border-gray-800">
		<span class="text-xl">🦖</span>
		<span class="font-semibold text-lg">컴퓨터 선택</span>
		<button
			onclick={() => goto('/settings')}
			class="ml-auto p-2 rounded-lg hover:bg-gray-800 transition-colors"
		>
			⚙️
		</button>
	</header>
	<div class="flex-1 overflow-y-auto px-4 py-6 space-y-3">
		<p class="text-gray-400 text-sm mb-4">대화할 컴퓨터를 선택하세요. 이름을 탭하면 편집할 수 있습니다.</p>
		{#each instances as inst}
			{@const customName = settings.getInstanceName(inst.id, inst.name)}
			<div class="bg-gray-900 rounded-xl p-4 space-y-3">
				<div class="flex items-center gap-3">
					<span class="text-3xl">🖥️</span>
					<div class="flex-1">
						<input
							type="text"
							value={customName}
							onchange={(e) => settings.setInstanceName(inst.id, (e.target as HTMLInputElement).value || inst.name)}
							class="bg-transparent text-white font-medium text-lg border-b border-transparent focus:border-blue-500 outline-none w-full"
							placeholder={inst.name}
						/>
						<p class="text-sm text-gray-400 mt-1">
							{inst.name} · {inst.status} · {new Date(inst.connectedAt).toLocaleString('ko-KR')}
						</p>
					</div>
				</div>
				<button
					onclick={() => selectInstance(inst.id)}
					class="w-full px-4 py-2.5 bg-blue-600 hover:bg-blue-500 rounded-lg font-medium transition-colors"
				>
					연결하기
				</button>
			</div>
		{/each}
	</div>
	<div class="px-4 pb-6">
		<button
			onclick={checkConnection}
			class="w-full px-4 py-3 bg-gray-700 hover:bg-gray-600 rounded-xl font-medium transition-colors"
		>
			🔄 새로고침
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
				onclick={() => { stt?.stop(); appState = 'select-instance'; }}
				class="flex items-center gap-1.5 px-2 py-1 rounded-lg hover:bg-gray-800 transition-colors"
				title="컴퓨터 변경"
			>
				<span class="text-xl">🦖</span>
				<span class="font-semibold text-lg">{settings.getInstanceName(settings.selectedInstance, '렉스')}</span>
				<span class="text-xs text-gray-500">▼</span>
			</button>
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
						{#if message.downloads && message.downloads.length > 0}
							<div class="mt-2 space-y-1.5 border-t border-gray-700 pt-2">
								{#each message.downloads as dl}
									<button
										onclick={() => handleDownload(dl)}
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
