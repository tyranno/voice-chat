/**
 * Native TTS — Uses Android built-in TextToSpeech engine (no network, instant)
 */
import { registerPlugin } from '@capacitor/core';
import type { TTSCallbacks } from './capacitor';

interface NativeAudioPlugin {
	speak(opts: { text: string }): Promise<void>;
	stop(): Promise<void>;
	setRate(opts: { rate: number }): Promise<void>;
	addListener(event: string, cb: (data: any) => void): any;
}

const NativeAudio = registerPlugin<NativeAudioPlugin>('NativeAudio');

function cleanForTTS(text: string): string {
	return text
		.replace(/https?:\/\/\S+/g, '')
		.replace(/#{1,6}\s*/g, '')
		.replace(/\*{1,3}([^*]+)\*{1,3}/g, '$1')
		.replace(/_{1,3}([^_]+)_{1,3}/g, '$1')
		.replace(/~~([^~]+)~~/g, '$1')
		.replace(/`([^`]+)`/g, '$1')
		.replace(/```[\s\S]*?```/g, '')
		.replace(/^[\s]*[-*+•]\s*/gm, '')
		.replace(/^[\s]*\d+\.\s*/gm, '')
		.replace(/[_~`|>\\<\[\]{}()#*=+\-]/g, ' ')
		.replace(/[\u{1F600}-\u{1F9FF}]/gu, '')
		.replace(/\s+/g, ' ')
		.trim();
}

function splitSentences(text: string): string[] {
	const cleaned = cleanForTTS(text);
	if (!cleaned) return [];
	const parts = cleaned.match(/[^.!?。\n]+[.!?。]?/g) || [cleaned];
	return parts
		.map((s) => s.trim())
		.filter((s) => s.length > 2);
}

export class CloudTTS {
	private queue: string[] = [];
	private _isSpeaking = false;
	private callbacks: TTSCallbacks;
	private cancelled = false;
	private playing = false;
	private rate: number;

	get isSpeaking() { return this._isSpeaking; }
	get _speaking() { return this._isSpeaking; }
	get available() { return true; }

	constructor(callbacks: TTSCallbacks, _serverUrl: string, _voice?: string, rate?: number) {
		this.callbacks = callbacks;
		this.rate = rate ?? 1.0;
	}

	setRate(rate: number) {
		this.rate = rate;
		NativeAudio.setRate({ rate }).catch(() => {});
	}

	speak(text: string) {
		const sentences = splitSentences(text);
		this.queue.push(...sentences);
		this.kickStart();
	}

	addChunk(text: string) {
		const sentences = splitSentences(text);
		if (sentences.length === 0) return;
		this.cancelled = false;
		this.queue.push(...sentences);
		if (!this.playing) {  // Only kickStart if not already playing
			this.kickStart();
		}
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
				console.log(`[TTS] "${text.substring(0, 30)}"`);

				try {
					await NativeAudio.speak({ text });
				} catch (e) {
					console.error('[TTS] Error:', e);
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
		await NativeAudio.stop().catch(() => {});
		if (this._isSpeaking) {
			this._isSpeaking = false;
			this.callbacks.onEnd();
		}
	}
}
