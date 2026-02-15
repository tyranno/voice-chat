import { Capacitor, registerPlugin } from '@capacitor/core';

interface FileDownloaderPlugin {
	download(opts: { url: string; filename?: string }): Promise<{ success: boolean; filename: string }>;
	openFile(opts: { filename: string }): Promise<{ success: boolean }>;
	addListener(event: 'downloadProgress', fn: (data: { progress: number; downloaded: number; total: number }) => void): Promise<{ remove: () => void }>;
	addListener(event: 'downloadComplete', fn: (data: { status: string; filename: string }) => void): Promise<{ remove: () => void }>;
}

const FileDownloader = registerPlugin<FileDownloaderPlugin>('FileDownloader');

export interface DownloadState {
	status: 'idle' | 'downloading' | 'complete' | 'error';
	progress: number;
	filename: string;
	error?: string;
}

export async function downloadFile(
	url: string,
	filename?: string,
	onProgress?: (percent: number) => void
): Promise<{ success: boolean; filename?: string; error?: string }> {
	if (!Capacitor.isNativePlatform()) {
		// Fallback: open in browser
		window.open(url, '_blank');
		return { success: true, filename: filename || 'download' };
	}

	try {
		let progressHandle: { remove: () => void } | null = null;
		if (onProgress) {
			progressHandle = await FileDownloader.addListener('downloadProgress', (data) => {
				onProgress(data.progress);
			});
		}

		const result = await FileDownloader.download({ url, filename });

		if (progressHandle) progressHandle.remove();
		return { success: result.success, filename: result.filename };
	} catch (e: any) {
		return { success: false, error: e.message };
	}
}

export async function openDownloadedFile(filename: string): Promise<{ success: boolean; error?: string }> {
	if (!Capacitor.isNativePlatform()) {
		return { success: false, error: 'Only available on Android' };
	}
	try {
		const result = await FileDownloader.openFile({ filename });
		return { success: result.success };
	} catch (e: any) {
		return { success: false, error: e.message };
	}
}

/**
 * Extract downloadable file URLs from a message text.
 * Matches common file extensions in URLs.
 */
export function extractFileUrls(text: string): { url: string; filename: string }[] {
	const urlRegex = /https?:\/\/[^\s<>"')\]]+/gi;
	const matches = text.match(urlRegex);
	if (!matches) return [];

	const fileExtensions = /\.(pdf|doc|docx|xls|xlsx|ppt|pptx|zip|rar|7z|tar|gz|mp3|mp4|avi|mkv|mov|wav|flac|jpg|jpeg|png|gif|webp|svg|txt|csv|json|xml|html|apk|exe|dmg|iso)(\?[^\s]*)?$/i;

	const results: { url: string; filename: string }[] = [];
	const seen = new Set<string>();

	for (const url of matches) {
		// Clean trailing punctuation
		let cleanUrl = url.replace(/[.,;:!?)}\]]+$/, '');
		if (seen.has(cleanUrl)) continue;
		seen.add(cleanUrl);

		if (fileExtensions.test(cleanUrl)) {
			const path = cleanUrl.split('?')[0];
			const segments = path.split('/');
			const filename = decodeURIComponent(segments[segments.length - 1]);
			results.push({ url: cleanUrl, filename });
		}
	}

	return results;
}
