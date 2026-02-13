/**
 * Capacitor native TTS wrapper
 * Uses @capacitor-community/text-to-speech for Android/iOS
 */
import { TextToSpeech } from '@capacitor-community/text-to-speech';

export interface TTSCallbacks {
	onStart: () => void;
	onEnd: () => void;
	onSentence: (text: string) => void;
}

export class CapacitorTTS {
	private queue: string[] = [];
	private _isSpeaking = false;
	private callbacks: TTSCallbacks;
	private cancelled = false;
	private playing = false;  // guard against concurrent playNext

	get isSpeaking() {
		return this._isSpeaking;
	}

	get available() {
		return true;
	}

	constructor(callbacks: TTSCallbacks) {
		this.callbacks = callbacks;
	}

	speak(text: string) {
		const sentences = splitSentences(text);
		this.queue.push(...sentences);
		this.kickStart();
	}

	addChunk(text: string) {
		const sentences = splitSentences(text);
		if (sentences.length === 0) return;
		this.cancelled = false;  // Reset cancel on new content
		this.queue.push(...sentences);
		this.kickStart();
	}

	private kickStart() {
		if (!this._isSpeaking) {
			this._isSpeaking = true;
			this.cancelled = false;
			this.callbacks.onStart();
		}
		if (!this.playing) {
			this.playNext();
		}
	}

	private async playNext() {
		if (this.playing) return;
		this.playing = true;

		try {
			while (this.queue.length > 0 && !this.cancelled) {
				const text = this.queue.shift()!;
				this.callbacks.onSentence(text);

				try {
					await TextToSpeech.speak({
						text,
						lang: 'ko-KR',
						rate: 1.1,
						pitch: 1.0,
						volume: 1.0,
						category: 'playback'
					});
				} catch (e) {
					console.error('[TTS] speak error:', e);
					// Don't break the loop — try next sentence
				}
			}
		} finally {
			this.playing = false;
			if (this._isSpeaking) {
				this._isSpeaking = false;
				this.callbacks.onEnd();
			}
		}
	}

	async stop() {
		this.cancelled = true;
		this.queue = [];
		this.playing = false;
		try {
			await TextToSpeech.stop();
		} catch {}
		if (this._isSpeaking) {
			this._isSpeaking = false;
			this.callbacks.onEnd();
		}
	}
}

function splitSentences(text: string): string[] {
	if (!text.trim()) return [];
	const parts = text.match(/[^.!?。]+[.!?。]?/g) || [text];
	return parts.map((s) => s.trim()).filter((s) => s.length > 0);
}
