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

export async function streamChat(messages: Message[], callbacks: StreamCallbacks): Promise<void> {
	let response: Response;
	try {
		response = await fetch(settings.chatEndpoint, {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json',
				'Authorization': `Bearer ${settings.authToken}`
			},
			body: JSON.stringify({
				instanceId: settings.selectedInstance,
				messages
			})
		});
	} catch (err) {
		callbacks.onError(new Error(`연결 실패: ${settings.serverUrl} 에 접속할 수 없습니다`));
		return;
	}

	if (!response.ok) {
		const errText = await response.text().catch(() => '');
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
