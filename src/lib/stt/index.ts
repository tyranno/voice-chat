/**
 * STT factory — auto-selects native (Android/iOS) or Web Speech API
 */
import { Capacitor } from '@capacitor/core';
import type { STTCallbacks } from './webspeech';

export type { STTCallbacks };

export interface STTEngine {
	isListening: boolean;
	start(lang?: string): void;
	stop(): void;
}

export function createSTT(callbacks: STTCallbacks): STTEngine {
	if (Capacitor.isNativePlatform()) {
		// Lazy import to avoid loading native plugin on web
		const { NativeSpeechSTT } = require('./native');
		return new NativeSpeechSTT(callbacks);
	} else {
		const { WebSpeechSTT } = require('./webspeech');
		return new WebSpeechSTT(callbacks);
	}
}
