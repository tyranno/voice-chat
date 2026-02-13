/**
 * Native STT using @capacitor-community/speech-recognition
 * Works on Android/iOS via Capacitor
 */
import { SpeechRecognition } from '@capacitor-community/speech-recognition';
import type { STTCallbacks } from './webspeech';

export class NativeSpeechSTT {
	private callbacks: STTCallbacks;
	private _isListening = false;
	private lang = 'ko-KR';

	get isListening() {
		return this._isListening;
	}

	constructor(callbacks: STTCallbacks) {
		this.callbacks = callbacks;
	}

	async start(lang = 'ko-KR') {
		this.lang = lang;

		// Check/request permission
		const permStatus = await SpeechRecognition.checkPermissions();
		if (permStatus.speechRecognition !== 'granted') {
			const req = await SpeechRecognition.requestPermissions();
			if (req.speechRecognition !== 'granted') {
				this.callbacks.onError('마이크 권한이 거부되었습니다');
				return;
			}
		}

		// Check availability
		const { available } = await SpeechRecognition.available();
		if (!available) {
			this.callbacks.onError('음성 인식을 사용할 수 없습니다');
			return;
		}

		this.stop();

		// Listen for partial results
		SpeechRecognition.addListener('partialResults', (data: any) => {
			const matches = data.matches || [];
			if (matches.length > 0) {
				this.callbacks.onInterim(matches[0]);
			}
		});

		// Listen for state changes
		SpeechRecognition.addListener('listeningState', (data: any) => {
			if (data.status === 'stopped' && this._isListening) {
				this._isListening = false;
				this.callbacks.onEnd();
			}
		});

		try {
			await SpeechRecognition.start({
				language: lang,
				maxResults: 1,
				partialResults: true,
				popup: false
			});
			this._isListening = true;
		} catch (err) {
			this.callbacks.onError(err instanceof Error ? err.message : '음성 인식 시작 실패');
		}
	}

	async stop() {
		this._isListening = false;
		try {
			await SpeechRecognition.removeAllListeners();
			await SpeechRecognition.stop();
		} catch {}
	}
}
