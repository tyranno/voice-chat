/**
 * Conversation API client — talks to GCP server
 */
import { settings } from '$lib/stores/settings.svelte';

export interface ConversationMeta {
	id: string;
	title: string;
	createdAt: number;
	updatedAt: number;
	messageCount: number;
}

export interface ConversationMessage {
	role: 'user' | 'assistant';
	content: string;
	timestamp?: number;
}

const baseUrl = () => settings.serverUrl;

export async function listConversations(): Promise<ConversationMeta[]> {
	try {
		const res = await fetch(`${baseUrl()}/api/conversations`);
		if (!res.ok) return [];
		const data = await res.json();
		return Array.isArray(data) ? data : [];
	} catch {
		return [];
	}
}

export async function createConversation(title = '새 대화'): Promise<ConversationMeta> {
	const res = await fetch(`${baseUrl()}/api/conversations`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ title })
	});
	if (!res.ok) throw new Error('Failed to create conversation');
	return res.json();
}

export async function getMessages(conversationId: string): Promise<ConversationMessage[]> {
	try {
		const res = await fetch(`${baseUrl()}/api/conversations/${conversationId}/messages`);
		if (!res.ok) return [];
		const data = await res.json();
		return Array.isArray(data) ? data : [];
	} catch {
		return [];
	}
}

export async function saveMessages(conversationId: string, messages: ConversationMessage[]): Promise<void> {
	await fetch(`${baseUrl()}/api/conversations/${conversationId}/messages`, {
		method: 'PUT',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(messages)
	});
}

export async function deleteConversation(conversationId: string): Promise<void> {
	await fetch(`${baseUrl()}/api/conversations/${conversationId}`, {
		method: 'DELETE'
	});
}

export async function updateTitle(conversationId: string, title: string): Promise<void> {
	await fetch(`${baseUrl()}/api/conversations/${conversationId}`, {
		method: 'PATCH',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ title })
	});
}
