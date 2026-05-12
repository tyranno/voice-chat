/**
 * 전역 백그라운드 음악 상태 — 어느 페이지든 현재 재생을 표시할 수 있게.
 * 첫 호출 시 1회 listener 등록 + 즉시 status ping.
 */
import { Capacitor } from '@capacitor/core';
import { onStatus, requestStatus } from '$lib/audio/backgroundAudio';

class BgAudioStore {
	playing = $state(false);
	playWhenReady = $state(false);
	state = $state<'idle' | 'buffering' | 'ready' | 'playing' | 'paused' | 'ended' | 'error'>('idle');
	title = $state('');
	artist = $state('');
	currentUrl = $state('');
	positionMs = $state(0);
	durationMs = $state(0);
	#started = false;

	async ensureStarted() {
		if (this.#started) return;
		if (!Capacitor.isNativePlatform()) return;
		this.#started = true;
		try {
			await onStatus((s) => {
				this.playing = s.playing;
				this.playWhenReady = s.playWhenReady ?? s.playing;
				if (s.state) this.state = s.state;
				if (s.title) this.title = s.title;
				if (s.artist) this.artist = s.artist;
				if (s.currentUrl) this.currentUrl = s.currentUrl;
				if (typeof s.positionMs === 'number') this.positionMs = Math.max(0, s.positionMs);
				if (typeof s.durationMs === 'number') this.durationMs = Math.max(0, s.durationMs);
			});
			await requestStatus().catch(() => {});
		} catch (e) {
			console.warn('[BgAudioStore] failed to attach', e);
		}
	}

	get isActive() {
		return (
			!!this.currentUrl &&
			(this.state === 'playing' || this.state === 'buffering' || this.playWhenReady)
		);
	}

	get isPausedReady() {
		return !!this.currentUrl && this.state === 'paused';
	}

	reset() {
		this.playing = false;
		this.playWhenReady = false;
		this.state = 'idle';
		this.title = '';
		this.artist = '';
		this.currentUrl = '';
		this.positionMs = 0;
		this.durationMs = 0;
	}
}

export const bgAudio = new BgAudioStore();
