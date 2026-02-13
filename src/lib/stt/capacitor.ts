/**
 * Capacitor Speech Recognition STT wrapper
 * Uses patched @capgo/capacitor-speech-recognition with continuous mode.
 * 
 * continuous: true → native auto-restart (100ms gap, no JS roundtrip)
 * The mic NEVER turns off unless stop() is called.
 */
import { SpeechRecognition } from '@capgo/capacitor-speech-recognition';

export interface STTCallbacks {
	onInterim: (text: string) => void;
	onFinal: (text: string) => void;
	onError: (error: string) => void;
	onEnd: () => void;
}

export class CapacitorSTT {
	private callbacks: STTCallbacks;
	private _isListening = false;
	private _paused = false;
	private lang = 'ko-KR';
	private lastText = '';
	private silenceTimer: ReturnType<typeof setTimeout> | null = null;

	get isListening() {
		return this._isListening;
	}

	constructor(callbacks: STTCallbacks) {
		this.callbacks = callbacks;
	}

	async start(lang = 'ko-KR') {
		if (this._isListening) return;
		this.lang = lang;
		this._paused = false;

		try {
			const permStatus = await SpeechRecognition.checkPermissions();
			if (permStatus.speechRecognition !== 'granted') {
				const result = await SpeechRecognition.requestPermissions();
				if (result.speechRecognition !== 'granted') {
					this.callbacks.onError('마이크 권한이 거부되었습니다');
					return;
				}
			}

			const { available } = await SpeechRecognition.available();
			if (!available) {
				this.callbacks.onError('이 기기에서 음성인식을 사용할 수 없습니다');
				return;
			}

			this._isListening = true;
			await this.beginSession();
		} catch (err) {
			this.callbacks.onError(`음성인식 오류: ${err}`);
			this._isListening = false;
		}
	}

	pause() {
		if (!this._isListening) return;
		this._paused = true;
		this.flushText();
		// stop() tells native to stop continuous mode
		try { SpeechRecognition.stop(); } catch {}
		try { SpeechRecognition.removeAllListeners(); } catch {}
		console.log('[STT] Paused');
	}

	async resume() {
		if (!this._isListening) {
			await this.start(this.lang);
			return;
		}
		this._paused = false;
		await this.beginSession();
		console.log('[STT] Resumed');
	}

	private flushText() {
		if (this.silenceTimer) {
			clearTimeout(this.silenceTimer);
			this.silenceTimer = null;
		}
		if (this.lastText.trim()) {
			const text = this.lastText.trim();
			this.lastText = '';
			this.callbacks.onFinal(text);
		}
	}

	private startSilenceTimer() {
		if (this.silenceTimer) clearTimeout(this.silenceTimer);
		this.silenceTimer = setTimeout(() => {
			if (this._isListening && !this._paused && this.lastText.trim()) {
				console.log('[STT] Silence 3s → send');
				const text = this.lastText.trim();
				this.lastText = '';
				this.callbacks.onFinal(text);
			}
		}, 3000);
	}

	private async beginSession() {
		try {
			await SpeechRecognition.removeAllListeners();

			SpeechRecognition.addListener('partialResults', (data: any) => {
				if (this._paused) return;
				if (data.matches && data.matches.length > 0) {
					const text = data.matches[0];
					this.lastText = text;
					this.callbacks.onInterim(text);
					this.startSilenceTimer();
				}
			});

			SpeechRecognition.addListener('segmentResults', (data: any) => {
				if (this._paused) return;
				if (data.matches && data.matches.length > 0) {
					const text = data.matches[0].trim();
					if (text) {
						this.lastText = '';
						if (this.silenceTimer) { clearTimeout(this.silenceTimer); this.silenceTimer = null; }
						this.callbacks.onFinal(text);
					}
				}
			});

			// These are just for logging — native handles restart
			SpeechRecognition.addListener('listeningState', (state: any) => {
				console.log('[STT] listeningState:', state.status);
			});

			SpeechRecognition.addListener('endOfSegmentedSession', () => {
				console.log('[STT] Segmented session ended (native will restart)');
				this.flushText();
			});

			await (SpeechRecognition as any).start({
				language: this.lang,
				maxResults: 1,
				partialResults: true,
				popup: false,
				allowForSilence: 10000,
				continuous: true  // NEW: native auto-restart
			});

			console.log('[STT] Started (continuous native mode)');

		} catch (err) {
			console.log(`[STT] Start error: ${err}`);
			// Retry once after 1s
			if (this._isListening && !this._paused) {
				setTimeout(() => {
					if (this._isListening && !this._paused) this.beginSession();
				}, 1000);
			}
		}
	}

	async stop() {
		this._isListening = false;
		this._paused = false;
		this.flushText();
		try {
			await SpeechRecognition.stop();
			await SpeechRecognition.removeAllListeners();
		} catch {}
		this.callbacks.onEnd();
	}
}
