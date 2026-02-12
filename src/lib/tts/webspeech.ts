/**
 * Web Speech API TTS wrapper
 * Sentence-by-sentence playback with queue
 */

export interface TTSCallbacks {
	onStart: () => void;
	onEnd: () => void;
	onSentence: (text: string) => void;
}

export class WebSpeechTTS {
	private synth: SpeechSynthesis;
	private queue: string[] = [];
	private _isSpeaking = false;
	private callbacks: TTSCallbacks;
	private cancelled = false;
	private voice: SpeechSynthesisVoice | null = null;

	get isSpeaking() {
		return this._isSpeaking;
	}

	constructor(callbacks: TTSCallbacks) {
		this.synth = window.speechSynthesis;
		this.callbacks = callbacks;
		this.pickVoice();
	}

	private pickVoice() {
		const tryPick = () => {
			const voices = this.synth.getVoices();
			// Prefer Korean voice
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

	/** Add text to queue and start speaking */
	speak(text: string) {
		// Split into sentences
		const sentences = splitSentences(text);
		this.queue.push(...sentences);
		if (!this._isSpeaking) {
			this._isSpeaking = true;
			this.cancelled = false;
			this.callbacks.onStart();
			this.playNext();
		}
	}

	/** Immediately add a single chunk (for streaming) */
	addChunk(text: string) {
		const sentences = splitSentences(text);
		if (sentences.length === 0) return;
		this.queue.push(...sentences);
		if (!this._isSpeaking && !this.cancelled) {
			this._isSpeaking = true;
			this.callbacks.onStart();
			this.playNext();
		}
	}

	private playNext() {
		if (this.cancelled || this.queue.length === 0) {
			this._isSpeaking = false;
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

	/** Stop immediately (barge-in) */
	stop() {
		this.cancelled = true;
		this.queue = [];
		this.synth.cancel();
		this._isSpeaking = false;
		this.callbacks.onEnd();
	}
}

/** Split text into sentence-like chunks */
function splitSentences(text: string): string[] {
	if (!text.trim()) return [];
	// Split on Korean/general sentence endings
	const parts = text.match(/[^.!?。]+[.!?。]?/g) || [text];
	return parts.map((s) => s.trim()).filter((s) => s.length > 0);
}
