/**
 * Settings store — persisted to localStorage
 */

const STORAGE_KEY = 'voicechat-settings';

interface Settings {
	serverUrl: string;
	selectedInstance: string;
	instanceNames: Record<string, string>; // id → custom name
	ttsEngine: 'native' | 'webspeech' | 'elevenlabs';
	sttEngine: 'webspeech' | 'deepgram';
	language: string;
}

const defaults: Settings = {
	serverUrl: 'https://voicechat.tyranno.xyz',
	selectedInstance: '',
	instanceNames: {},
	ttsEngine: 'native',
	sttEngine: 'webspeech',
	language: 'ko-KR'
};

function load(): Settings {
	if (typeof localStorage === 'undefined') return { ...defaults };
	try {
		const raw = localStorage.getItem(STORAGE_KEY);
		if (!raw) return { ...defaults };
		const saved = { ...defaults, ...JSON.parse(raw) };
		// v6 migration: force native TTS on upgrade
		if (saved.ttsEngine === 'webspeech' && saved.sttEngine === 'webspeech') {
			saved.ttsEngine = 'native';
			saved.sttEngine = 'vosk';
			localStorage.setItem(STORAGE_KEY, JSON.stringify(saved));
		}
		return saved;
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

	get isConfigured() { return !!this.#settings.serverUrl; }

	get selectedInstance() { return this.#settings.selectedInstance; }
	set selectedInstance(v: string) { this.#settings.selectedInstance = v; save(this.#settings); }

	getInstanceName(id: string, fallback: string) {
		return this.#settings.instanceNames[id] || fallback;
	}
	setInstanceName(id: string, name: string) {
		this.#settings.instanceNames[id] = name;
		save(this.#settings);
	}

	get ttsEngine() { return this.#settings.ttsEngine; }
	set ttsEngine(v: 'native' | 'webspeech' | 'elevenlabs') { this.#settings.ttsEngine = v; save(this.#settings); }

	get sttEngine() { return this.#settings.sttEngine; }
	set sttEngine(v: 'webspeech' | 'deepgram') { this.#settings.sttEngine = v; save(this.#settings); }

	get language() { return this.#settings.language; }
	set language(v: string) { this.#settings.language = v; save(this.#settings); }

	get healthEndpoint() { return `${this.serverUrl}/health`; }
	get instancesEndpoint() { return `${this.serverUrl}/api/instances`; }
	get chatEndpoint() { return `${this.serverUrl}/api/chat`; }
}

export const settings = new SettingsStore();
