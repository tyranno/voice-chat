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
	import {
		listConversations, createConversation, getMessages,
		saveMessages as serverSaveMessages, deleteConversation as serverDeleteConversation,
		type ConversationMeta
	} from '$lib/api/conversations';
	import { onFcmNotification, type Notification } from '$lib/api/notifications';
	import { addNotification } from '$lib/stores/notifications.svelte';
	import { initMusicHistory, addToHistory, savePlaylist, getHistory, getPlaylists, deletePlaylist, type MusicPlaylist } from '$lib/stores/musicHistory.svelte';
	import { registerFcmToken } from '$lib/api/fcm';

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
	let showSidebar = $state(false);
	let currentConversationId = $state<string | null>(null);
	let conversationList = $state<ConversationMeta[]>([]);
	let musicVideoId = $state<string | null>(null);
	let musicTitle = $state('');
	let musicIframe: HTMLIFrameElement | null = null;
	let musicExpanded = $state(false);
	let musicPlaylist = $state<Array<{ videoId: string; title: string }>>([]);
	let musicIndex = $state(0);
	let musicSpeed = $state(1.0);

	function musicCommand(cmd: string, args: any[] = []) {
		if (!musicIframe?.contentWindow) return;
		musicIframe.contentWindow.postMessage(JSON.stringify({
			event: 'command', func: cmd, args: args
		}), '*');
	}
	function pauseMusic() { musicCommand('pauseVideo'); }
	function resumeMusic() { musicCommand('playVideo'); }
	function muteMusic() { musicCommand('mute'); }
	function unmuteMusic() { musicCommand('unMute'); }
	function setPlaybackRate(rate: number) {
		musicSpeed = rate;
		musicCommand('setPlaybackRate', [rate]);
	}

	function playMusicFromPlaylist(index: number) {
		if (index < 0 || index >= musicPlaylist.length) return;
		musicIndex = index;
		const item = musicPlaylist[index];
		musicVideoId = item.videoId;
		musicTitle = item.title;
		musicSpeed = 1.0;
		addToHistory(item.videoId, item.title);
	}

	function nextTrack() {
		if (musicIndex < musicPlaylist.length - 1) {
			playMusicFromPlaylist(musicIndex + 1);
		}
	}

	function prevTrack() {
		if (musicIndex > 0) {
			playMusicFromPlaylist(musicIndex - 1);
		}
	}
	let messagesContainer: HTMLDivElement;
	let showTextInput = $state(false);
	let showDropdown = $state(false);

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
	const FINAL_DEBOUNCE_MS = 1000;  // final 결과 후 1초 대기 (추가 음성 없으면 전송)

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

	async function persistMessages() {
		if (!currentConversationId) return;
		try {
			await serverSaveMessages(currentConversationId, messages.map(m => ({ role: m.role, content: m.content })));
			await refreshConversationList();
		} catch (e) { console.error('[Conversations] Save failed:', e); }
	}

	async function refreshConversationList() {
		try { conversationList = await listConversations(); } catch {}
	}

	async function switchConversation(id: string) {
		await persistMessages();
		try {
			const loaded = await getMessages(id);
			messages = loaded.map(m => ({ role: m.role as 'user' | 'assistant', content: m.content }));
			currentConversationId = id;
			// 대화 로드 후 맨 아래로 스크롤
			setTimeout(() => scrollToBottom(), 100);
		} catch (e) { addDebug(`대화 로드 실패: ${e}`); }
		showSidebar = false;
	}

	async function startNewConversation() {
		await persistMessages();
		try {
			const conv = await createConversation();
			currentConversationId = conv.id;
			messages = [];
			await refreshConversationList();
		} catch (e) { addDebug(`새 대화 생성 실패: ${e}`); }
		showSidebar = false;
	}

	async function handleDeleteConversation(id: string, e: Event) {
		e.stopPropagation();
		try {
			await serverDeleteConversation(id);
			if (id === currentConversationId) { messages = []; await startNewConversation(); }
			await refreshConversationList();
		} catch {}
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

	async function selectInstance(id: string) {
		settings.selectedInstance = id;
		appState = 'connected';
		// 대화 초기화 (다른 장비의 대화)
		messages = [];
		currentConversationId = null;
		try {
			conversationList = await listConversations();
			if (conversationList.length > 0) {
				currentConversationId = conversationList[0].id;
				const loaded = await getMessages(currentConversationId);
				if (loaded.length > 0) {
					messages = loaded.map(m => ({ role: m.role as 'user' | 'assistant', content: m.content }));
					setTimeout(() => scrollToBottom(), 100);
				}
			}
		} catch {}
		// 인스턴스 선택 즉시 마이크 자동 ON
		if (stt && Capacitor.isNativePlatform()) {
			conversation.micEnabled = true;
			conversation.setListening();
			addDebug('[VoiceChat] 마이크 자동 시작');
			stt.start().catch((e: any) => console.warn('[VoiceChat] Auto-mic failed:', e));
		}
	}

	let showExitConfirm = $state(false);

	onMount(async () => {
		// 뒤로가기 버튼 처리 (네이티브 hardwareBackPress 이벤트)
		window.addEventListener('hardwareBackPress', () => {
			if (showExitConfirm) {
				showExitConfirm = false;
			} else if (showSidebar) {
				showSidebar = false;
			} else if (musicExpanded) {
				musicExpanded = false;
			} else if (appState === 'select-instance') {
				if (settings.selectedInstance) {
					appState = 'connected';
				} else {
					showExitConfirm = true;
				}
			} else if (appState === 'no-server' || appState === 'no-instance') {
				showExitConfirm = true;
			} else if (appState === 'connected') {
				// 채팅창에서 뒤로가기 → 종료 확인
				showExitConfirm = true;
			}
		});

		try {
		addDebug(`Platform: ${Capacitor.getPlatform()}`);
		initMusicHistory();

		// Register FCM token
		registerFcmToken().then(token => {
			if (token) addDebug(`FCM 등록 완료`);
		});

		// Listen for FCM notifications (forwarded from native)
		onFcmNotification((notif) => {
			addDebug(`🔔 ${notif.title}: ${notif.message}`);
			addNotification(notif);
			const text = notif.title ? `${notif.title}. ${notif.message}` : notif.message;
			if (tts && text && conversation.micEnabled) {
				tts.speak(text);
			}
		});

		// Load conversations from server
		try {
			conversationList = await listConversations();
			if (conversationList.length > 0) {
				currentConversationId = conversationList[0].id;
				const loaded = await getMessages(currentConversationId);
				if (loaded.length > 0) {
					messages = loaded.map(m => ({ role: m.role as 'user' | 'assistant', content: m.content }));
					addDebug(`대화 복원: ${loaded.length}개 메시지`);
					setTimeout(() => scrollToBottom(), 100);
				}
			}
		} catch (e) { addDebug(`대화 목록 로드: ${e}`); }

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
				// 음악 재생 중 음성 감지 시 일시정지
				if (musicVideoId && text.trim()) pauseMusic();
			},
			onFinal: (text: string) => {
				const trimmed = text.trim();
				// 빈 결과 및 placeholder 필터링
				if (trimmed && trimmed !== '인식 중...' && trimmed !== '인식 중') {
					finalBuffer += (finalBuffer ? ' ' : '') + trimmed;
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

	async function handleMusicRequest(text: string): Promise<boolean> {
		// 멈춤/정지
		if (/(?:노래|음악|곡)?\s*(?:멈춰|정지|꺼|중지|스톱|stop)/.test(text)) {
			if (musicVideoId) {
				musicVideoId = null;
				musicTitle = '';
				musicPlaylist = [];
				messages.push({ role: 'user', content: text });
				messages.push({ role: 'assistant', content: '🎵 음악을 멈췄습니다.' });
				tts?.speak('음악을 멈췄습니다.');
				return true;
			}
			return false;
		}

		// 다음 곡
		if (/(?:다음|넥스트|next)\s*(?:곡|노래|음악)?/.test(text) && musicVideoId) {
			if (musicIndex < musicPlaylist.length - 1) {
				nextTrack();
				messages.push({ role: 'user', content: text });
				messages.push({ role: 'assistant', content: `🎵 다음 곡: "${musicTitle}"` });
				tts?.speak(`다음 곡, ${musicTitle}`);
			} else {
				messages.push({ role: 'user', content: text });
				messages.push({ role: 'assistant', content: '🎵 마지막 곡입니다.' });
				tts?.speak('마지막 곡입니다.');
			}
			return true;
		}

		// 이전 곡
		if (/(?:이전|이전곡|previous|prev)\s*(?:곡|노래|음악)?/.test(text) && musicVideoId) {
			if (musicIndex > 0) {
				prevTrack();
				messages.push({ role: 'user', content: text });
				messages.push({ role: 'assistant', content: `🎵 이전 곡: "${musicTitle}"` });
				tts?.speak(`이전 곡, ${musicTitle}`);
			} else {
				messages.push({ role: 'user', content: text });
				messages.push({ role: 'assistant', content: '🎵 첫 번째 곡입니다.' });
				tts?.speak('첫 번째 곡입니다.');
			}
			return true;
		}

		// 빠르게/느리게 재생
		const speedMatch = text.match(/(?:(\d(?:\.\d)?)\s*배속)|(?:(빠르게|빨리|느리게|천천히|보통|원래)\s*(?:재생)?)/);
		if (speedMatch && musicVideoId) {
			let speed = 1.0;
			if (speedMatch[1]) {
				speed = parseFloat(speedMatch[1]);
			} else if (speedMatch[2]) {
				const cmd = speedMatch[2];
				if (cmd === '빠르게' || cmd === '빨리') speed = 1.5;
				else if (cmd === '느리게' || cmd === '천천히') speed = 0.75;
				else speed = 1.0;
			}
			speed = Math.max(0.25, Math.min(2.0, speed));
			setPlaybackRate(speed);
			messages.push({ role: 'user', content: text });
			messages.push({ role: 'assistant', content: `🎵 ${speed}배속으로 재생합니다.` });
			tts?.speak(`${speed}배속으로 재생합니다.`);
			return true;
		}

		// 음악 재생 키워드 감지
		const musicPatterns = [
			/(.+?)\s*(?:노래|음악|곡)\s*(?:틀어|재생|검색|찾아|들려)/,
			/(?:노래|음악|곡)\s*(?:틀어|재생|검색|찾아|들려)\s*(.+)/,
			/(.+?)\s*(?:틀어줘|재생해줘|들려줘|플레이)/,
			/(?:다른|다음)\s*(?:노래|음악|곡)\s*(?:틀어|재생)/,
		];

		let searchQuery = '';
		for (const pattern of musicPatterns) {
			const match = text.match(pattern);
			if (match && match[1]) {
				searchQuery = match[1].replace(/(?:노래|음악|곡|좀|해서|해줘|줘|다른|다음)/g, '').trim();
				break;
			}
		}
		if (!searchQuery) return false;

		addDebug(`🎵 음악 요청 감지: "${searchQuery}"`);
		messages.push({ role: 'user', content: text });
		messages.push({ role: 'assistant', content: `🎵 "${searchQuery}" 검색 중...` });
		const idx = messages.length - 1;

		try {
			const res = await fetch(`${settings.serverUrl}/api/youtube/search?q=${encodeURIComponent(searchQuery)}`);
			if (!res.ok) throw new Error('검색 실패');
			const results = await res.json();
			if (!results || results.length === 0) {
				messages[idx].content = `검색 결과가 없습니다: "${searchQuery}"`;
				tts?.speak(`${searchQuery} 검색 결과가 없습니다.`);
				return true;
			}
			const first = results[0];
			messages[idx].content = `🎵 "${first.title}" 재생합니다.`;
			tts?.speak(`${first.title} 재생합니다.`);
			// 플레이리스트 저장 + 미니 플레이어에서 재생
			musicPlaylist = results.map((r: any) => ({ videoId: r.videoId, title: r.title }));
			musicIndex = 0;
			musicVideoId = first.videoId;
			musicTitle = first.title;
			musicSpeed = 1.0;
			addToHistory(first.videoId, first.title);
			savePlaylist(searchQuery, musicPlaylist);
			persistMessages();
		} catch (e) {
			messages[idx].content = `음악 검색 오류: ${e}`;
			tts?.speak('음악 검색에 실패했습니다.');
		}
		return true;
	}

	async function sendMessage(text?: string) {
		const finalText = text || input.trim();
		if (!finalText) return;

		// 응답 중이면 큐잉 (텍스트 입력도 큐잉 가능)
		if (isLoading) {
			pendingMessage = finalText;
			input = '';
			addDebug(`📋 큐잉: "${finalText}" (응답 대기 중)`);
			return;
		}
		addDebug(`📤 sendMessage: "${finalText}"`);

		// 대화 ID가 없으면 자동 생성
		if (!currentConversationId) {
			try {
				const conv = await createConversation(finalText.substring(0, 30));
				currentConversationId = conv.id;
				await refreshConversationList();
				addDebug(`새 대화 자동 생성: ${conv.id}`);
			} catch (e) { addDebug(`대화 생성 실패: ${e}`); }
		}

		// 음악 재생 중이면 일시정지
		if (musicVideoId) pauseMusic();

		// 음악 요청이면 YouTube 검색으로 처리
		if (await handleMusicRequest(finalText)) {
			input = '';
			return;
		}

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
							messages[assistantIdx] = { ...messages[assistantIdx], content: fullResponse };
							scrollToBottom();
							if (fullResponse.length <= 30) addDebug(`📥 delta: "${delta}"`);

							// TTS: 문장 단위로 즉시 재생 (마이크 켜진 경우만)
							sentenceBuffer += delta;
							const sentenceEnd = sentenceBuffer.match(/[.!?。\n]/);
							if (sentenceEnd && sentenceBuffer.trim().length > 10) {
								if (conversation.micEnabled) tts?.addChunk(sentenceBuffer.trim());
								sentenceBuffer = '';
							}
						},
						onDone: () => {
							addDebug(`✅ 응답완료: ${fullResponse.length}자`);
							if (sentenceBuffer.trim()) {
								addDebug(`🔊 TTS: "${sentenceBuffer.trim().substring(0, 30)}"`);
								if (conversation.micEnabled) tts?.addChunk(sentenceBuffer.trim());
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
						onError: (err) => { addDebug(`❌ API에러: ${err}`); isLoading = false; reject(err); }
					},
					0,
					currentConversationId || undefined
				);
			});
		} catch (err) {
			messages[assistantIdx].content = `⚠️ 오류: ${err instanceof Error ? err.message : '알 수 없는 오류'}`;
		} finally {
			isLoading = false;
			persistMessages();  // 서버에 대화 저장

			// AI 응답 완료 후 음악 재개 (TTS 끝난 뒤)
			if (musicVideoId) {
				const waitForTts = () => {
					if (tts && (tts as any)._isSpeaking) {
						setTimeout(waitForTts, 500);
					} else {
						resumeMusic();
					}
				};
				setTimeout(waitForTts, 1000);
			}

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
	<!-- Header (간소화) -->
	<header class="flex-shrink-0 flex items-center justify-between px-3 py-2 bg-gray-900 border-b border-gray-800" style="padding-top: env(safe-area-inset-top);">
		<div class="flex items-center gap-1.5">
			<button
				onclick={() => { showSidebar = !showSidebar; if (showSidebar) refreshConversationList(); }}
				class="p-1.5 rounded-lg hover:bg-gray-800 transition-colors text-sm"
				title="대화 목록"
			>☰</button>
			<button
				onclick={async () => { stt?.stop(); try { instances = await getInstances(); } catch {} appState = 'select-instance'; }}
				class="flex items-center gap-1 px-1.5 py-0.5 rounded-lg hover:bg-gray-800 transition-colors"
				title="컴퓨터 변경"
			>
				<span class="text-lg">🦖</span>
				<span class="font-medium text-sm">{settings.getInstanceName(settings.selectedInstance, '렉스')}</span>
			</button>
			<span
				class="text-[10px] px-1.5 py-0.5 rounded-full"
				style="background-color: {conversation.stateColor}20; color: {conversation.stateColor}"
			>
				{conversation.stateLabel}
			</span>
		</div>
		<div class="flex items-center gap-1">
			<button onclick={() => { showTextInput = !showTextInput; }} class="p-1.5 rounded-lg hover:bg-gray-800 transition-colors text-sm" title="텍스트 입력">⌨️</button>
			<button onclick={() => goto('/settings')} class="p-1.5 rounded-lg hover:bg-gray-800 transition-colors text-sm" title="설정">⚙️</button>
			<div class="relative">
				<button
					onclick={() => showDropdown = !showDropdown}
					class="p-1.5 rounded-lg hover:bg-gray-800 transition-colors text-sm"
					title="메뉴"
				>⋯</button>
				{#if showDropdown}
					<div class="fixed inset-0 z-40" onclick={() => showDropdown = false}></div>
					<div class="absolute right-0 top-full mt-1 z-50 w-44 bg-gray-800 border border-gray-700 rounded-xl shadow-2xl overflow-hidden">
						<button onclick={() => { showDropdown = false; startNewConversation(); }} class="w-full text-left px-3 py-2.5 hover:bg-gray-700 transition-colors text-sm flex items-center gap-2">
							<span>✏️</span><span>새 대화</span>
						</button>
						<button onclick={() => { showDropdown = false; goto('/notifications'); }} class="w-full text-left px-3 py-2.5 hover:bg-gray-700 transition-colors text-sm flex items-center gap-2">
							<span>🔔</span><span>알림</span>
						</button>
						<button onclick={() => { showDropdown = false; goto('/music'); }} class="w-full text-left px-3 py-2.5 hover:bg-gray-700 transition-colors text-sm flex items-center gap-2">
							<span>🎵</span><span>음악</span>
						</button>
					</div>
				{/if}
			</div>
		</div>
	</header>

	<!-- Sidebar overlay -->
	{#if showSidebar}
		<div class="fixed inset-0 z-50 flex">
			<div class="absolute inset-0 bg-black/60" onclick={() => showSidebar = false}></div>
			<div class="relative w-72 max-w-[80vw] bg-gray-900 h-full flex flex-col shadow-2xl" style="padding-top: env(safe-area-inset-top);">
				<div class="flex items-center justify-between px-4 py-3 border-b border-gray-800">
					<span class="font-semibold text-lg">💬 대화 목록</span>
					<button onclick={startNewConversation} class="px-3 py-1.5 bg-blue-600 hover:bg-blue-500 rounded-lg text-sm font-medium transition-colors">+ 새 대화</button>
				</div>
				<div class="flex-1 overflow-y-auto">
					{#each conversationList as conv}
						<div
							role="button" tabindex="0"
							onclick={() => switchConversation(conv.id)}
							onkeydown={(e) => { if (e.key === 'Enter') switchConversation(conv.id); }}
							class="w-full text-left px-4 py-3 border-b border-gray-800/50 hover:bg-gray-800 transition-colors group cursor-pointer
								{conv.id === currentConversationId ? 'bg-gray-800/70' : ''}"
						>
							<div class="flex items-start justify-between gap-2">
								<div class="flex-1 min-w-0">
									<p class="text-sm font-medium truncate">{conv.title}</p>
									<p class="text-xs text-gray-500 mt-0.5">
										{new Date(conv.updatedAt).toLocaleDateString('ko-KR')} {new Date(conv.updatedAt).toLocaleTimeString('ko-KR', {hour: '2-digit', minute: '2-digit'})}
										· {conv.messageCount}개
									</p>
								</div>
								<span
									role="button" tabindex="-1"
									onclick={(e) => handleDeleteConversation(conv.id, e)}
									onkeydown={(e) => { if (e.key === 'Enter') handleDeleteConversation(conv.id, e); }}
									class="opacity-0 group-hover:opacity-100 p-1 text-gray-500 hover:text-red-400 transition-all cursor-pointer"
									title="삭제"
								>🗑</span>
							</div>
						</div>
					{/each}
					{#if conversationList.length === 0}
						<div class="px-4 py-8 text-center text-gray-500 text-sm">대화 내역이 없습니다</div>
					{/if}
				</div>
			</div>
		</div>
	{/if}

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

	<!-- Waveform + Interim (고정 영역 - 겹침 방지) -->
	<div class="flex-shrink-0 px-4 py-2 space-y-1 bg-gray-950" style="padding-bottom: env(safe-area-inset-bottom);">
		{#if sttError}
			<div class="text-center text-xs text-red-400 bg-red-900/30 rounded-lg px-2 py-1.5">
				⚠️ {sttError}
				<button onclick={() => sttError = ''} class="ml-1 text-red-300 hover:text-white">✕</button>
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
				onclick={toggleMic}
				class="w-14 h-14 rounded-full flex items-center justify-center text-xl transition-all duration-300 {conversation.micEnabled
					? 'bg-red-600 hover:bg-red-500 shadow-lg shadow-red-600/30 scale-110'
					: 'bg-gray-700 hover:bg-gray-600'}"
			>
				{conversation.micEnabled ? '🎤' : '🎙️'}
			</button>
		</div>
	</div>

	<!-- Music Player -->
	{#if musicVideoId}
		{#if musicExpanded}
			<!-- 전체 화면 -->
			<div class="fixed inset-0 z-50 bg-black flex flex-col" style="padding-top: env(safe-area-inset-top); padding-bottom: env(safe-area-inset-bottom);">
				<div class="flex items-center justify-between px-4 py-3 bg-gray-900">
					<div class="flex items-center gap-2 flex-1 min-w-0">
						<span class="text-lg">🎵</span>
						<p class="text-sm text-white truncate">{musicTitle || '재생 중'}</p>
						<span class="text-xs text-gray-500">{musicIndex + 1}/{musicPlaylist.length}</span>
					</div>
					<div class="flex gap-2">
						<button onclick={() => musicExpanded = false} class="px-3 py-1.5 text-xs bg-gray-700 hover:bg-gray-600 rounded-lg">▼ 축소</button>
						<button onclick={() => { musicVideoId = null; musicTitle = ''; musicExpanded = false; musicPlaylist = []; }} class="px-3 py-1.5 text-xs bg-red-700 hover:bg-red-600 rounded-lg">⏹</button>
					</div>
				</div>
				<!-- 컨트롤 바 -->
				<div class="flex items-center justify-center gap-4 px-4 py-2 bg-gray-900/80">
					<button onclick={prevTrack} disabled={musicIndex <= 0} class="px-3 py-2 text-lg bg-gray-700 hover:bg-gray-600 rounded-lg disabled:opacity-30">⏮</button>
					<button onclick={pauseMusic} class="px-3 py-2 text-lg bg-gray-700 hover:bg-gray-600 rounded-lg">⏸</button>
					<button onclick={resumeMusic} class="px-3 py-2 text-lg bg-gray-700 hover:bg-gray-600 rounded-lg">▶</button>
					<button onclick={nextTrack} disabled={musicIndex >= musicPlaylist.length - 1} class="px-3 py-2 text-lg bg-gray-700 hover:bg-gray-600 rounded-lg disabled:opacity-30">⏭</button>
					<select onchange={(e) => setPlaybackRate(parseFloat((e.target as HTMLSelectElement).value))} class="px-2 py-2 text-xs bg-gray-700 rounded-lg text-white">
						<option value="0.5" selected={musicSpeed === 0.5}>0.5x</option>
						<option value="0.75" selected={musicSpeed === 0.75}>0.75x</option>
						<option value="1" selected={musicSpeed === 1.0}>1x</option>
						<option value="1.25" selected={musicSpeed === 1.25}>1.25x</option>
						<option value="1.5" selected={musicSpeed === 1.5}>1.5x</option>
						<option value="2" selected={musicSpeed === 2.0}>2x</option>
					</select>
				</div>
				<div class="flex-1 relative">
					<iframe
						bind:this={musicIframe}
						src={`https://www.youtube.com/embed/${musicVideoId}?autoplay=1&playsinline=1&enablejsapi=1&origin=${encodeURIComponent('https://localhost')}`}
						style="position: absolute; top: 0; left: 0; width: 100%; height: 100%;"
						allow="autoplay; encrypted-media"
						allowfullscreen
						title="Music Player"
					></iframe>
				</div>
			</div>
		{:else}
			<!-- 미니 플레이어 -->
			<div class="flex-shrink-0 bg-gray-900 border-t border-gray-800 px-3 py-2">
				<div class="flex items-center gap-1.5">
					<button onclick={prevTrack} disabled={musicIndex <= 0} class="p-1 text-sm disabled:opacity-30">⏮</button>
					<span class="text-sm">🎵</span>
					<p class="flex-1 text-xs text-gray-300 truncate">{musicTitle || '재생 중'} <span class="text-gray-500">({musicIndex+1}/{musicPlaylist.length})</span></p>
					<button onclick={nextTrack} disabled={musicIndex >= musicPlaylist.length - 1} class="p-1 text-sm disabled:opacity-30">⏭</button>
					<button onclick={() => musicExpanded = true} class="px-2 py-1 text-xs bg-gray-700 hover:bg-gray-600 rounded-lg">▲</button>
					<button onclick={() => { musicVideoId = null; musicTitle = ''; musicPlaylist = []; }} class="px-2 py-1 text-xs bg-red-700 hover:bg-red-600 rounded-lg">⏹</button>
				</div>
				<div class="mt-1 rounded-lg overflow-hidden" style="height: 0; padding-bottom: 20%; position: relative;">
					<iframe
						bind:this={musicIframe}
						src={`https://www.youtube.com/embed/${musicVideoId}?autoplay=1&playsinline=1&enablejsapi=1&origin=${encodeURIComponent('https://localhost')}`}
						style="position: absolute; top: 0; left: 0; width: 100%; height: 100%;"
						allow="autoplay; encrypted-media"
						allowfullscreen
						title="Music Player"
					></iframe>
				</div>
			</div>
		{/if}
	{/if}

	<!-- Text input (toggle) -->
	{#if showTextInput}
		<div class="px-4 pb-4 pt-2">
			<div class="flex gap-2">
				<input
					type="text"
					bind:value={input}
					onkeydown={handleKeydown}
					placeholder={isLoading ? "응답 중... (전송하면 대기열에 추가)" : "메시지를 입력하세요..."}
					class="flex-1 px-4 py-3 bg-gray-800 border border-gray-700 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
				/>
				<button
					onclick={() => sendMessage()}
					disabled={!input.trim()}
					class="px-4 py-3 bg-blue-600 text-white rounded-xl font-medium hover:bg-blue-500 disabled:opacity-50 transition-colors"
				>
					{isLoading ? '대기' : '전송'}
				</button>
			</div>
		</div>
	{/if}


</div>
{/if}

<!-- 종료 확인 다이얼로그 -->
{#if showExitConfirm}
<div class="fixed inset-0 z-[100] flex items-center justify-center bg-black/70">
	<div class="bg-gray-900 rounded-2xl p-6 mx-8 max-w-sm w-full shadow-2xl">
		<p class="text-white text-lg font-semibold text-center mb-2">앱 종료</p>
		<p class="text-gray-400 text-center text-sm mb-6">앱을 종료하시겠습니까?</p>
		<div class="flex gap-3">
			<button
				onclick={() => showExitConfirm = false}
				class="flex-1 px-4 py-2.5 bg-gray-700 hover:bg-gray-600 rounded-xl font-medium text-white transition-colors"
			>취소</button>
			<button
				onclick={() => { import('@capacitor/app').then(({ App }) => App.exitApp()); }}
				class="flex-1 px-4 py-2.5 bg-red-600 hover:bg-red-500 rounded-xl font-medium text-white transition-colors"
			>종료</button>
		</div>
	</div>
</div>
{/if}
