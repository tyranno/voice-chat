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

	/** Exposed for external checks (e.g., STT resume logic) */
	get _speaking() {
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

/**
 * Strip markdown, special chars, URLs etc. for natural TTS output
 */
function cleanForTTS(text: string): string {
	return text
		// Remove URLs
		.replace(/https?:\/\/\S+/g, '')
		// Remove markdown headers
		.replace(/#{1,6}\s*/g, '')
		// Remove bold/italic markers
		.replace(/\*{1,3}([^*]+)\*{1,3}/g, '$1')
		.replace(/_{1,3}([^_]+)_{1,3}/g, '$1')
		// Remove strikethrough
		.replace(/~~([^~]+)~~/g, '$1')
		// Remove inline code backticks
		.replace(/`([^`]+)`/g, '$1')
		// Remove code blocks
		.replace(/```[\s\S]*?```/g, '')
		// Remove bullet points and list markers
		.replace(/^[\s]*[-*+•]\s*/gm, '')
		.replace(/^[\s]*\d+\.\s*/gm, '')
		// Remove special characters that sound weird when read
		.replace(/[_~`|>\\<\[\]{}()#*=+\-]/g, ' ')
		// Remove emoji (optional - keep common ones)
		.replace(/[\u{1F600}-\u{1F9FF}]/gu, '')
		// Collapse multiple spaces
		.replace(/\s+/g, ' ')
		.trim();
}

function splitSentences(text: string): string[] {
	const cleaned = cleanForTTS(text);
	if (!cleaned) return [];
	const parts = cleaned.match(/[^.!?。\n]+[.!?。]?/g) || [cleaned];
	return parts.map((s) => s.trim()).filter((s) => s.length > 2);
}
