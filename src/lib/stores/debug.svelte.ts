/**
 * Debug log store - sliding window of recent log lines
 */

class DebugStore {
	#log = $state('');
	#maxChars = 4000;

	get log() { return this.#log; }

	add(msg: string) {
		const t = new Date().toLocaleTimeString('ko-KR');
		this.#log = `[${t}] ${msg}\n${this.#log}`.slice(0, this.#maxChars);
		if (typeof console !== 'undefined') console.log(`[Rex] ${msg}`);
	}

	clear() { this.#log = ''; }
}

export const debug = new DebugStore();
