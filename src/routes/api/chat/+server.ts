import { env } from '$env/dynamic/private';
import type { RequestHandler } from './$types';

const OPENCLAW_URL = env.OPENCLAW_URL || 'http://localhost:18789/v1/chat/completions';
const OPENCLAW_TOKEN = env.OPENCLAW_TOKEN || '';

export const POST: RequestHandler = async ({ request }) => {
	const body = await request.json();

	const headers: Record<string, string> = {
		'Content-Type': 'application/json',
		'x-openclaw-agent-id': 'main'
	};

	if (OPENCLAW_TOKEN) {
		headers['Authorization'] = `Bearer ${OPENCLAW_TOKEN}`;
	}

	const response = await fetch(OPENCLAW_URL, {
		method: 'POST',
		headers,
		body: JSON.stringify({
			model: 'openclaw',
			stream: true,
			user: 'voicechat-app',
			messages: body.messages
		})
	});

	if (!response.ok) {
		const errText = await response.text().catch(() => '');
		return new Response(JSON.stringify({ error: `Gateway error: ${response.status}`, detail: errText }), {
			status: response.status,
			headers: { 'Content-Type': 'application/json' }
		});
	}

	return new Response(response.body, {
		headers: {
			'Content-Type': 'text/event-stream',
			'Cache-Control': 'no-cache',
			Connection: 'keep-alive'
		}
	});
};
