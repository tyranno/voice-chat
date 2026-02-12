/**
 * Capacitor Speech Recognition STT wrapper
 * Simplified version for debugging
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

	get isListening() {
		return this._isListening;
	}

	constructor(callbacks: STTCallbacks) {
		this.callbacks = callbacks;
	}

	async start(lang = 'ko-KR') {
		this.lang = lang;
		this._isListening = true;
		
		try {
			this.callbacks.onError('1. 권한 확인 중...');
			
			// Check permissions
			const permStatus = await SpeechRecognition.checkPermissions();
			this.callbacks.onError(`2. 권한상태: ${permStatus.speechRecognition}`);
			
			if (permStatus.speechRecognition !== 'granted') {
				this.callbacks.onError('3. 권한 요청 중...');
				const result = await SpeechRecognition.requestPermissions();
				this.callbacks.onError(`4. 권한결과: ${result.speechRecognition}`);
				
				if (result.speechRecognition !== 'granted') {
					this.callbacks.onError('권한 거부됨');
					this._isListening = false;
					return;
				}
			}
			
			this.callbacks.onError('5. 음성인식 가능 확인...');
			const { available } = await SpeechRecognition.available();
			this.callbacks.onError(`6. 가능여부: ${available}`);
			
			if (!available) {
				this.callbacks.onError('음성인식 불가 (기기 미지원)');
				this._isListening = false;
				return;
			}
			
			this.callbacks.onError('7. 리스너 등록...');
			await SpeechRecognition.removeAllListeners();
			
			SpeechRecognition.addListener('partialResults', (data) => {
				if (data.matches && data.matches.length > 0) {
					this.callbacks.onInterim(data.matches[0]);
				}
			});
			
			this.callbacks.onError('8. 음성인식 시작!');
			const result = await SpeechRecognition.start({
				language: lang,
				maxResults: 1,
				partialResults: true,
				popup: false
			});
			
			this.callbacks.onError('9. 음성인식 완료');
			this._isListening = false;
			
			if (result.matches && result.matches.length > 0) {
				this.callbacks.onFinal(result.matches[0].trim());
			}
			
			this.callbacks.onEnd();
			
		} catch (err) {
			this.callbacks.onError(`에러: ${err}`);
			this._isListening = false;
		}
	}

	async stop() {
		this._isListening = false;
		try {
			await SpeechRecognition.stop();
			await SpeechRecognition.removeAllListeners();
		} catch (err) {
			// ignore
		}
	}
}
