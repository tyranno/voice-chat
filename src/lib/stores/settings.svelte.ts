/**
 * Settings store — persisted to localStorage
 */

const STORAGE_KEY = 'voicechat-settings';

interface Settings {
	gatewayUrl: string;
	gatewayToken: string;
	ttsEngine: 'webspeech' | 'elevenlabs';
	sttEngine: 'webspeech' | 'deepgram';
	language: string;
}

const defaults: Settings = {
	gatewayUrl: 'http://192.168.0.10:18789',
	gatewayToken: '',
	ttsEngine: 'webspeech',
	sttEngine: 'webspeech',
	language: 'ko-KR'
};

function load(): Settings {
	if (typeof localStorage === 'undefined') return { ...defaults };
	try {
		const raw = localStorage.getItem(STORAGE_KEY);
		if (!raw) return { ...defaults };
		return { ...defaults, ...JSON.parse(raw) };
	} catch {
		return { ...defaults };
	}
}

function save(s: Settings) {
	if (typeof localStorage === 'undefined') return;
	localStorage.setItem(STORAGE_KEY, JSON.stringify(s));
}

class SettingsStore {
	#settings: Settings = $state(load());

	get gatewayUrl() { return this.#settings.gatewayUrl; }
	set gatewayUrl(v: string) { this.#settings.gatewayUrl = v; save(this.#settings); }

	get gatewayToken() { return this.#settings.gatewayToken; }
	set gatewayToken(v: string) { this.#settings.gatewayToken = v; save(this.#settings); }

	get ttsEngine() { return this.#settings.ttsEngine; }
	set ttsEngine(v: 'webspeech' | 'elevenlabs') { this.#settings.ttsEngine = v; save(this.#settings); }

	get sttEngine() { return this.#settings.sttEngine; }
	set sttEngine(v: 'webspeech' | 'deepgram') { this.#settings.sttEngine = v; save(this.#settings); }

	get language() { return this.#settings.language; }
	set language(v: string) { this.#settings.language = v; save(this.#settings); }

	get chatEndpoint() {
		return `${this.gatewayUrl}/v1/chat/completions`;
	}
}

export const settings = new SettingsStore();
