/**
 * Settings store — persisted to localStorage
 */

const STORAGE_KEY = 'voicechat-settings';

interface Settings {
	serverUrl: string;
	authToken: string;
	selectedInstance: string;
	ttsEngine: 'webspeech' | 'elevenlabs';
	sttEngine: 'webspeech' | 'deepgram';
	language: string;
}

const defaults: Settings = {
	serverUrl: '',
	authToken: '',
	selectedInstance: '',
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

	get serverUrl() { return this.#settings.serverUrl; }
	set serverUrl(v: string) { this.#settings.serverUrl = v; save(this.#settings); }

	get authToken() { return this.#settings.authToken; }
	set authToken(v: string) { this.#settings.authToken = v; save(this.#settings); }

	get selectedInstance() { return this.#settings.selectedInstance; }
	set selectedInstance(v: string) { this.#settings.selectedInstance = v; save(this.#settings); }

	get ttsEngine() { return this.#settings.ttsEngine; }
	set ttsEngine(v: 'webspeech' | 'elevenlabs') { this.#settings.ttsEngine = v; save(this.#settings); }

	get sttEngine() { return this.#settings.sttEngine; }
	set sttEngine(v: 'webspeech' | 'deepgram') { this.#settings.sttEngine = v; save(this.#settings); }

	get language() { return this.#settings.language; }
	set language(v: string) { this.#settings.language = v; save(this.#settings); }

	/** Health check endpoint */
	get healthEndpoint() {
		return `${this.serverUrl}/health`;
	}

	/** Instances list endpoint */
	get instancesEndpoint() {
		return `${this.serverUrl}/api/instances`;
	}

	/** Chat endpoint */
	get chatEndpoint() {
		return `${this.serverUrl}/api/chat`;
	}
}

export const settings = new SettingsStore();
