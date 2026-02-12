/**
 * OpenClaw Gateway client — direct SSE streaming from browser
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
	const headers: Record<string, string> = {
		'Content-Type': 'application/json',
		'x-openclaw-agent-id': 'main'
	};

	if (settings.gatewayToken) {
		headers['Authorization'] = `Bearer ${settings.gatewayToken}`;
	}

	let response: Response;
	try {
		response = await fetch(settings.chatEndpoint, {
			method: 'POST',
			headers,
			body: JSON.stringify({
				model: 'openclaw',
				stream: true,
				user: 'voicechat-app',
				messages
			})
		});
	} catch (err) {
		callbacks.onError(new Error(`연결 실패: ${settings.gatewayUrl} 에 접속할 수 없습니다`));
		return;
	}

	if (!response.ok) {
		const errText = await response.text().catch(() => '');
		callbacks.onError(new Error(`Gateway 오류 ${response.status}: ${errText}`));
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
					const delta = parsed.choices?.[0]?.delta?.content;
					if (delta) {
						callbacks.onDelta(delta);
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
