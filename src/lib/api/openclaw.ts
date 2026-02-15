/**
 * Chat client — streams via VoiceChat server relay to OpenClaw bridge
 */
import { settings } from '$lib/stores/settings.svelte';

interface Message {
	role: 'user' | 'assistant' | 'system';
	content: string;
}

interface StreamCallbacks {
	onDelta: (text: string) => void;
	onDone: () => void;
	onError: (error: Error) => void;
}

async function fetchOnce(url: string, init: RequestInit): Promise<Response> {
	const controller = new AbortController();
	const timeout = setTimeout(() => controller.abort(), 15000);
	try {
		const res = await fetch(url, { ...init, signal: controller.signal });
		return res;
	} finally {
		clearTimeout(timeout);
	}
}

export async function streamChat(messages: Message[], callbacks: StreamCallbacks): Promise<void> {
	let response: Response;
	try {
		response = await fetchOnce(settings.chatEndpoint, {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json'
			},
			body: JSON.stringify({
				instanceId: settings.selectedInstance,
				messages
			})
		});
	} catch (err) {
		callbacks.onError(new Error(`연결 실패: ${settings.serverUrl}`));
		return;
	}

	if (!response.ok) {
		const errText = await response.text().catch(() => '');
		if (response.status === 404 && errText.includes('Instance not found')) {
			// Instance ID changed — try to auto-recover
			try {
				const { getInstances } = await import('./instances');
				const instances = await getInstances();
				if (instances.length > 0) {
					settings.selectedInstance = instances[0].id;
					console.log(`[VoiceChat] Instance auto-recovered: ${instances[0].id}`);
					// Retry with new instance
					return streamChat(messages, callbacks);
				}
			} catch {}
		}
		callbacks.onError(new Error(`서버 오류 ${response.status}: ${errText}`));
		return;
	}

	if (!response.body) {
		callbacks.onError(new Error('응답 본문이 없습니다'));
		return;
	}

	const reader = response.body.getReader();
	const decoder = new TextDecoder();
	let buffer = '';

	try {
		while (true) {
			const { done, value } = await reader.read();
			if (done) break;

			buffer += decoder.decode(value, { stream: true });
			const lines = buffer.split('\n');
			buffer = lines.pop() || '';

			for (const line of lines) {
				if (!line.startsWith('data: ')) continue;
				const data = line.slice(6);
				if (data === '[DONE]') {
					callbacks.onDone();
					return;
				}

				try {
					const parsed = JSON.parse(data);
					if (parsed.error) {
						callbacks.onError(new Error(parsed.error));
						return;
					}
					if (parsed.delta) {
						callbacks.onDelta(parsed.delta);
					}
				} catch {
					// skip malformed JSON
				}
			}
		}
		callbacks.onDone();
	} catch (err) {
		callbacks.onError(err instanceof Error ? err : new Error(String(err)));
	}
}
