import { registerPlugin } from '@capacitor/core';

export interface BackgroundAudioStatus {
	playing: boolean;
	playWhenReady?: boolean;
	buffering: boolean;
	currentUrl?: string;
	title?: string;
	artist?: string;
	positionMs: number;
	durationMs: number;
	index: number;
	hasNext: boolean;
	hasPrev: boolean;
	error?: string;
	state?: 'idle' | 'buffering' | 'ready' | 'playing' | 'paused' | 'ended' | 'error';
	playbackState?: string;
}

export interface PlayOptions {
	url: string;
	title?: string;
	artist?: string;
	playlist?: string[];
	index?: number;
	durationMs?: number; // optional duration hint (e.g. from MediaStore for saved tracks)
}

interface BackgroundAudioPlugin {
	play(options: PlayOptions): Promise<void>;
	pause(): Promise<void>;
	resume(): Promise<void>;
	stop(): Promise<void>;
	next(): Promise<void>;
	prev(): Promise<void>;
	seek(options: { positionMs: number }): Promise<void>;
	setRate(options: { rate: number }): Promise<void>;
	getStatus(): Promise<{ requested: boolean }>;
	addListener(
		eventName: 'status',
		listenerFunc: (status: BackgroundAudioStatus) => void
	): Promise<{ remove: () => Promise<void> }>;
}

const BackgroundAudio = registerPlugin<BackgroundAudioPlugin>('BackgroundAudio');

export const play = (options: PlayOptions) => BackgroundAudio.play(options);
export const pause = () => BackgroundAudio.pause();
export const resume = () => BackgroundAudio.resume();
export const stop = () => BackgroundAudio.stop();
export const next = () => BackgroundAudio.next();
export const prev = () => BackgroundAudio.prev();
export const seek = (positionMs: number) => BackgroundAudio.seek({ positionMs });
export const setRate = (rate: number) => BackgroundAudio.setRate({ rate });
export const requestStatus = () => BackgroundAudio.getStatus();

export const onStatus = async (callback: (status: BackgroundAudioStatus) => void) => {
	const handle = await BackgroundAudio.addListener('status', callback);
	return () => handle.remove();
};
