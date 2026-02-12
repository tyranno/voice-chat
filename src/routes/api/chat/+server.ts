import type { RequestHandler } from './$types';

const OPENCLAW_URL = 'http://localhost:18789/v1/chat/completions';

export const POST: RequestHandler = async ({ request }) => {
	const body = await request.json();

	const response = await fetch(OPENCLAW_URL, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			'x-openclaw-agent-id': 'main'
		},
		body: JSON.stringify({
			model: 'openclaw',
			stream: true,
			user: 'voicechat-app',
			messages: body.messages
		})
	});

	if (!response.ok) {
		return new Response(JSON.stringify({ error: `Gateway error: ${response.status}` }), {
			status: response.status,
			headers: { 'Content-Type': 'application/json' }
		});
	}

	// Proxy the SSE stream
	return new Response(response.body, {
		headers: {
			'Content-Type': 'text/event-stream',
			'Cache-Control': 'no-cache',
			Connection: 'keep-alive'
		}
	});
};
