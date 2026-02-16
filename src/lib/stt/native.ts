/**
 * Native STT — NativeSttPlugin.java thin wrapper
 *
 * Java가 모든 걸 관리:
 * - SpeechRecognizer 생성/파괴/자동 재시작 (1500ms)
 * - ERROR_NO_MATCH, ERROR_SPEECH_TIMEOUT → 자동 재시작
 * - 중복 결과 필터링 (500ms 윈도우)
 * - mute/unmute 시스템 사운드
 *
 * JS는 이벤트만 수신:
 * - sttResult { type: 'partial'|'final'|'error', text: string }
 */
import { registerPlugin } from '@capacitor/core';
import type { PluginListenerHandle } from '@capacitor/core';

interface NativeSttPlugin {
	start(options?: Record<string, unknown>): Promise<void>;
	stop(options?: Record<string, unknown>): Promise<void>;
	pause(options?: Record<string, unknown>): Promise<void>;
	resume(options?: Record<string, unknown>): Promise<void>;
	isListening(options?: Record<string, unknown>): Promise<{ listening: boolean }>;
	muteSystemSounds(options?: Record<string, unknown>): Promise<void>;
	unmuteSystemSounds(options?: Record<string, unknown>): Promise<void>;
	addListener(
		event: 'sttResult',
		handler: (data: { type: string; text: string }) => void
	): Promise<PluginListenerHandle>;
	removeAllListeners(): Promise<void>;
}

const NativeStt = registerPlugin<NativeSttPlugin>('NativeStt');

interface NativeSTTCallbacks {
	onInterim: (text: string) => void;
	onFinal: (text: string) => void;
	onError: (error: string) => void;
	onEnd: () => void;
}

export class NativeSTT {
	private callbacks: NativeSTTCallbacks;
	private _isListening = false;
	private _paused = false;
	private _started = false;  // start()~stop() 사이
	private listenerHandle: PluginListenerHandle | null = null;
	private serverUrl: string;

	constructor(callbacks: NativeSTTCallbacks, serverUrl?: string) {
		this.callbacks = callbacks;
		this.serverUrl = serverUrl || '';
	}

	get isListening() { return this._isListening; }
	get isPaused() { return this._paused; }
	get isStarting() { return false; }  // Java가 관리 — JS에서 추적 불필요
	get isSessionActive() { return this._started; }
	get isRestartPending() { return false; }  // Java가 관리

	async start(): Promise<void> {
		if (this._started) return;
		
		this._paused = false;
		this._isListening = false;  // Reset before starting
		
		try {
			// 리스너 등록 (한 번만)
			if (!this.listenerHandle) {
				this.listenerHandle = await NativeStt.addListener('sttResult', (data) => {
					if (this._paused) return;

					console.log(`[NativeSTT] sttResult: type=${data.type} text=${data.text}`);

					if (data.type === 'partial') {
						// 서버 placeholder "인식 중..." 필터링
						if (data.text && data.text !== '인식 중...') {
							this.callbacks.onInterim(data.text);
						}
					} else if (data.type === 'final') {
						this._isListening = true;  // Java가 인식에 성공 = 활성 상태
						this.callbacks.onFinal(data.text);
					} else if (data.type === 'error') {
						this.callbacks.onError(data.text);
					}
				});
				console.log('[NativeSTT] Listener registered');
			}

			await NativeStt.start({ serverUrl: this.serverUrl });
			// Only set _started after successful start
			this._started = true;
			this._isListening = true;
			console.log('[NativeSTT] Started');
		} catch (e) {
			console.error('[NativeSTT] Start failed:', e);
			this._started = false;
			this._isListening = false;
			this.callbacks.onError(`STT 시작 실패: ${e}`);
		}
	}

	async stop(): Promise<void> {
		this._started = false;
		this._isListening = false;
		this._paused = false;
		try { await NativeStt.stop(); } catch {}
		this.callbacks.onEnd();
	}

	async pause(): Promise<void> {
		if (this._paused) return;
		console.log('[NativeSTT] Pause');
		this._paused = true;
		this._isListening = false;
		try { await NativeStt.pause(); } catch {}
	}

	async resume(): Promise<void> {
		if (!this._started) return;
		console.log('[NativeSTT] Resume');
		this._paused = false;
		try {
			await NativeStt.resume();
			this._isListening = true;
		} catch (e) {
			console.error('[NativeSTT] Resume failed:', e);
			// Don't set _isListening to true on failure
			this._paused = true;  // Revert to paused state
			this.callbacks.onError(`STT 재개 실패: ${e}`);
		}
	}

	async destroy(): Promise<void> {
		await this.stop();
		if (this.listenerHandle) {
			try { await this.listenerHandle.remove(); } catch {}
			this.listenerHandle = null;
		}
		try { await NativeStt.removeAllListeners(); } catch {}
	}
}
