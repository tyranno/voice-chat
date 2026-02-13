/**
 * Web Speech API TTS wrapper
 * Sentence-by-sentence playback with queue
 * Falls back gracefully when speechSynthesis is unavailable (e.g. Android WebView)
 */

export interface TTSCallbacks {
	onStart: () => void;
	onEnd: () => void;
	onSentence: (text: string) => void;
}

export class WebSpeechTTS {
	private synth: SpeechSynthesis | null;
	private queue: string[] = [];
	private _isSpeaking = false;
	private callbacks: TTSCallbacks;
	private cancelled = false;
	private voice: SpeechSynthesisVoice | null = null;
	private keepAliveTimer: ReturnType<typeof setInterval> | null = null;

	get isSpeaking() {
		return this._isSpeaking;
	}

	get available() {
		return !!this.synth;
	}

	constructor(callbacks: TTSCallbacks) {
		this.synth = typeof window !== 'undefined' && window.speechSynthesis ? window.speechSynthesis : null;
		this.callbacks = callbacks;
		if (this.synth) this.pickVoice();
	}

	private pickVoice() {
		if (!this.synth) return;
		const tryPick = () => {
			const voices = this.synth!.getVoices();
			this.voice =
				voices.find((v) => v.lang.startsWith('ko') && v.name.includes('Google')) ||
				voices.find((v) => v.lang.startsWith('ko')) ||
				null;
		};
		tryPick();
		if (this.synth.onvoiceschanged !== undefined) {
			this.synth.onvoiceschanged = tryPick;
		}
	}

	private startKeepAlive() {
		this.stopKeepAlive();
		// Chrome pauses speechSynthesis after ~15s; resume/pause keeps it alive
		this.keepAliveTimer = setInterval(() => {
			if (this.synth && this._isSpeaking) {
				this.synth.pause();
				this.synth.resume();
			}
		}, 10000);
	}

	private stopKeepAlive() {
		if (this.keepAliveTimer) {
			clearInterval(this.keepAliveTimer);
			this.keepAliveTimer = null;
		}
	}

	speak(text: string) {
		if (!this.synth) return;
		const sentences = splitSentences(text);
		this.queue.push(...sentences);
		if (!this._isSpeaking) {
			this._isSpeaking = true;
			this.cancelled = false;
			this.callbacks.onStart();
			this.startKeepAlive();
			this.playNext();
		}
	}

	addChunk(text: string) {
		if (!this.synth) return;
		const sentences = splitSentences(text);
		if (sentences.length === 0) return;
		this.queue.push(...sentences);
		if (!this._isSpeaking) {
			this._isSpeaking = true;
			this.cancelled = false;
			this.callbacks.onStart();
			this.startKeepAlive();
			this.playNext();
		}
	}

	private playNext() {
		if (!this.synth || this.cancelled || this.queue.length === 0) {
			this._isSpeaking = false;
			this.stopKeepAlive();
			this.callbacks.onEnd();
			return;
		}

		const text = this.queue.shift()!;
		this.callbacks.onSentence(text);

		const utterance = new SpeechSynthesisUtterance(text);
		utterance.lang = 'ko-KR';
		utterance.rate = 1.1;
		if (this.voice) utterance.voice = this.voice;

		utterance.onend = () => this.playNext();
		utterance.onerror = () => this.playNext();

		this.synth.speak(utterance);
	}

	stop() {
		this.cancelled = true;
		this.queue = [];
		this.stopKeepAlive();
		if (this.synth) this.synth.cancel();
		this._isSpeaking = false;
		this.callbacks.onEnd();
	}
}

function splitSentences(text: string): string[] {
	if (!text.trim()) return [];
	const parts = text.match(/[^.!?。]+[.!?。]?/g) || [text];
	return parts.map((s) => s.trim()).filter((s) => s.length > 0);
}
