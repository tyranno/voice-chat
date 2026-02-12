/**
 * Web Speech API STT wrapper
 * Chrome/Edge only
 */

export interface STTCallbacks {
	onInterim: (text: string) => void;
	onFinal: (text: string) => void;
	onError: (error: string) => void;
	onEnd: () => void;
}

export class WebSpeechSTT {
	private recognition: any = null;
	private callbacks: STTCallbacks;
	private _isListening = false;
	private restartOnEnd = false;
	private lang = 'ko-KR';

	get isListening() {
		return this._isListening;
	}

	constructor(callbacks: STTCallbacks) {
		this.callbacks = callbacks;
	}

	start(lang = 'ko-KR') {
		this.lang = lang;
		const W = window as any;
		const SpeechRecognition = W.SpeechRecognition || W.webkitSpeechRecognition;
		if (!SpeechRecognition) {
			this.callbacks.onError('Web Speech API not supported');
			return;
		}

		this.stop();

		const rec = new SpeechRecognition();
		rec.lang = lang;
		rec.continuous = true;
		rec.interimResults = true;
		rec.maxAlternatives = 1;

		rec.onresult = (e: any) => {
			let interim = '';
			for (let i = e.resultIndex; i < e.results.length; i++) {
				const transcript = e.results[i][0].transcript;
				if (e.results[i].isFinal) {
					this.callbacks.onFinal(transcript.trim());
				} else {
					interim += transcript;
				}
			}
			if (interim) {
				this.callbacks.onInterim(interim);
			}
		};

		rec.onerror = (e: any) => {
			if (e.error === 'no-speech' || e.error === 'aborted') return;
			this.callbacks.onError(e.error);
		};

		rec.onend = () => {
			this._isListening = false;
			if (this.restartOnEnd) {
				setTimeout(() => {
					if (this.restartOnEnd) this.start(this.lang);
				}, 100);
			} else {
				this.callbacks.onEnd();
			}
		};

		this.recognition = rec;
		this.restartOnEnd = true;
		this._isListening = true;
		rec.start();
	}

	stop() {
		this.restartOnEnd = false;
		this._isListening = false;
		if (this.recognition) {
			try {
				this.recognition.abort();
			} catch {}
			this.recognition = null;
		}
	}
}
