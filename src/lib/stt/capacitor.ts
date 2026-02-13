/**
 * Capacitor Speech Recognition STT wrapper
 * Uses @capacitor-community/speech-recognition for native Android/iOS
 */
import { SpeechRecognition } from '@capacitor-community/speech-recognition';

export interface STTCallbacks {
	onInterim: (text: string) => void;
	onFinal: (text: string) => void;
	onError: (error: string) => void;
	onEnd: () => void;
}

export class CapacitorSTT {
	private callbacks: STTCallbacks;
	private _isListening = false;
	private lang = 'ko-KR';
	private shouldRestart = false;

	get isListening() {
		return this._isListening;
	}

	constructor(callbacks: STTCallbacks) {
		this.callbacks = callbacks;
	}

	async start(lang = 'ko-KR') {
		this.lang = lang;
		this._isListening = true;
		this.shouldRestart = true;

		try {
			// Check permissions
			const permStatus = await SpeechRecognition.checkPermissions();
			if (permStatus.speechRecognition !== 'granted') {
				const result = await SpeechRecognition.requestPermissions();
				if (result.speechRecognition !== 'granted') {
					this.callbacks.onError('마이크 권한이 거부되었습니다');
					this._isListening = false;
					this.shouldRestart = false;
					return;
				}
			}

			// Check availability
			const { available } = await SpeechRecognition.available();
			if (!available) {
				this.callbacks.onError('이 기기에서 음성인식을 사용할 수 없습니다');
				this._isListening = false;
				this.shouldRestart = false;
				return;
			}

			await this.startListening();
		} catch (err) {
			this.callbacks.onError(`음성인식 오류: ${err}`);
			this._isListening = false;
			this.shouldRestart = false;
		}
	}

	private async startListening() {
		try {
			await SpeechRecognition.removeAllListeners();

			SpeechRecognition.addListener('partialResults', (data) => {
				if (data.matches && data.matches.length > 0) {
					this.callbacks.onInterim(data.matches[0]);
				}
			});

			const result = await SpeechRecognition.start({
				language: this.lang,
				maxResults: 1,
				partialResults: true,
				popup: false
			});

			this._isListening = false;

			if (result.matches && result.matches.length > 0) {
				this.callbacks.onFinal(result.matches[0].trim());
			}

			// Auto-restart for continuous listening (like WebSpeech continuous mode)
			if (this.shouldRestart) {
				setTimeout(() => {
					if (this.shouldRestart) {
						this._isListening = true;
						this.startListening();
					} else {
						this.callbacks.onEnd();
					}
				}, 100);
			} else {
				this.callbacks.onEnd();
			}
		} catch (err) {
			this._isListening = false;
			if (this.shouldRestart) {
				// Retry after brief pause
				setTimeout(() => {
					if (this.shouldRestart) {
						this._isListening = true;
						this.startListening();
					}
				}, 500);
			} else {
				this.callbacks.onError(`음성인식 오류: ${err}`);
			}
		}
	}

	async stop() {
		this.shouldRestart = false;
		this._isListening = false;
		try {
			await SpeechRecognition.stop();
			await SpeechRecognition.removeAllListeners();
		} catch {
			// ignore
		}
	}
}
