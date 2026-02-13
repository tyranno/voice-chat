/**
 * VOSK STT — Capacitor custom native plugin
 * Uses AudioRecord directly → mic NEVER auto-stops
 */
import { registerPlugin } from '@capacitor/core';
import type { PluginListenerHandle } from '@capacitor/core';

interface VoskSttPlugin {
	init(options: { serverUrl: string }): Promise<void>;
	start(): Promise<void>;
	stop(): Promise<void>;
	isListening(): Promise<{ listening: boolean }>;
	addListener(
		eventName: 'sttResult',
		handler: (event: { type: 'partial' | 'final'; text: string }) => void
	): Promise<PluginListenerHandle>;
}

const VoskStt = registerPlugin<VoskSttPlugin>('VoskStt');

interface VoskSTTCallbacks {
	onInterim: (text: string) => void;
	onFinal: (text: string) => void;
	onError: (error: string) => void;
	onEnd: () => void;
}

export class VoskSTT {
	private callbacks: VoskSTTCallbacks;
	private listener: PluginListenerHandle | null = null;
	private _isListening = false;
	private initialized = false;
	private serverUrl: string;

	constructor(callbacks: VoskSTTCallbacks, serverUrl: string = 'https://voicechat.tyranno.xyz') {
		this.callbacks = callbacks;
		this.serverUrl = serverUrl;
	}

	get isListening() {
		return this._isListening;
	}

	async init(): Promise<void> {
		if (this.initialized) return;
		try {
			await VoskStt.init({ serverUrl: this.serverUrl });
			this.initialized = true;
			console.log('[VoskSTT] Initialized with server:', this.serverUrl);
		} catch (e) {
			this.callbacks.onError(`VOSK 초기화 실패: ${e}`);
		}
	}

	async start(): Promise<void> {
		if (this._isListening) return;

		if (!this.initialized) {
			await this.init();
		}

		// Set up event listener
		this.listener = await VoskStt.addListener('sttResult', (event) => {
			if (event.type === 'partial') {
				this.callbacks.onInterim(event.text);
			} else if (event.type === 'final') {
				this.callbacks.onFinal(event.text);
			}
		});

		try {
			await VoskStt.start();
			this._isListening = true;
			console.log('[VoskSTT] Listening started — mic is ON');
		} catch (e) {
			this.callbacks.onError(`시작 실패: ${e}`);
		}
	}

	async stop(): Promise<void> {
		if (!this._isListening) return;

		try {
			await VoskStt.stop();
		} catch (e) {
			console.error('[VoskSTT] Stop error:', e);
		}

		if (this.listener) {
			await this.listener.remove();
			this.listener = null;
		}

		this._isListening = false;
		console.log('[VoskSTT] Stopped');
		this.callbacks.onEnd();
	}

	// Alias for compatibility with existing code
	async pause(): Promise<void> {
		await this.stop();
	}

	async resume(): Promise<void> {
		await this.start();
	}
}
