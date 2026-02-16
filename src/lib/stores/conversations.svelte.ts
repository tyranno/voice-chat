/**
 * Conversation history manager — persists to localStorage
 */

export interface ChatMessage {
	role: 'user' | 'assistant' | 'system';
	content: string;
	downloads?: { url: string; filename: string }[];
}

export interface Conversation {
	id: string;
	title: string;
	messages: ChatMessage[];
	createdAt: number;
	updatedAt: number;
}

const STORAGE_KEY = 'voicechat_conversations';
const CURRENT_KEY = 'voicechat_current_id';
const MAX_CONVERSATIONS = 50;

function generateId(): string {
	return `conv_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
}

function loadFromStorage(): Conversation[] {
	try {
		const raw = localStorage.getItem(STORAGE_KEY);
		return raw ? JSON.parse(raw) : [];
	} catch {
		return [];
	}
}

function saveToStorage(convs: Conversation[]) {
	try {
		// Keep only the latest MAX_CONVERSATIONS
		const trimmed = convs.slice(0, MAX_CONVERSATIONS);
		localStorage.setItem(STORAGE_KEY, JSON.stringify(trimmed));
	} catch (e) {
		console.error('[Conversations] Save failed:', e);
	}
}

function deriveTitle(messages: ChatMessage[]): string {
	const firstUser = messages.find(m => m.role === 'user');
	if (!firstUser) return '새 대화';
	const text = firstUser.content.trim();
	return text.length > 30 ? text.slice(0, 30) + '…' : text;
}

// --- Reactive state ---
let conversations = $state<Conversation[]>(loadFromStorage());
let currentId = $state<string | null>(localStorage.getItem(CURRENT_KEY));

export function getConversations(): Conversation[] {
	return conversations;
}

export function getCurrentId(): string | null {
	return currentId;
}

export function getCurrentConversation(): Conversation | null {
	if (!currentId) return null;
	return conversations.find(c => c.id === currentId) ?? null;
}

/** Load messages for a conversation */
export function loadConversation(id: string): ChatMessage[] {
	const conv = conversations.find(c => c.id === id);
	if (!conv) return [];
	currentId = id;
	localStorage.setItem(CURRENT_KEY, id);
	return [...conv.messages];
}

/** Start a new conversation, returns its ID */
export function newConversation(): string {
	const id = generateId();
	const conv: Conversation = {
		id,
		title: '새 대화',
		messages: [],
		createdAt: Date.now(),
		updatedAt: Date.now()
	};
	conversations = [conv, ...conversations];
	currentId = id;
	localStorage.setItem(CURRENT_KEY, id);
	saveToStorage(conversations);
	return id;
}

/** Save/update messages for the current conversation */
export function saveMessages(messages: ChatMessage[]) {
	if (!currentId) {
		// Auto-create if none
		currentId = newConversation();
	}
	const idx = conversations.findIndex(c => c.id === currentId);
	if (idx === -1) return;

	conversations[idx].messages = [...messages];
	conversations[idx].updatedAt = Date.now();
	conversations[idx].title = deriveTitle(messages);

	// Move to top
	if (idx > 0) {
		const [conv] = conversations.splice(idx, 1);
		conversations = [conv, ...conversations];
	}

	saveToStorage(conversations);
}

/** Delete a conversation */
export function deleteConversation(id: string) {
	conversations = conversations.filter(c => c.id !== id);
	if (currentId === id) {
		currentId = conversations.length > 0 ? conversations[0].id : null;
		if (currentId) {
			localStorage.setItem(CURRENT_KEY, currentId);
		} else {
			localStorage.removeItem(CURRENT_KEY);
		}
	}
	saveToStorage(conversations);
}

/** Ensure there's an active conversation */
export function ensureConversation(): string {
	if (currentId && conversations.find(c => c.id === currentId)) {
		return currentId;
	}
	return newConversation();
}
