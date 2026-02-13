/**
 * Conversation state machine
 * idle → listening → processing → speaking → listening (when mic on)
 * When micEnabled: state NEVER goes to idle
 */

export type ConversationState = 'idle' | 'listening' | 'processing' | 'speaking';

class ConversationStore {
	state: ConversationState = $state('idle');
	interimText: string = $state('');
	micEnabled: boolean = $state(false);

	get stateColor(): string {
		switch (this.state) {
			case 'listening':
				return '#3b82f6'; // blue
			case 'processing':
				return '#eab308'; // yellow
			case 'speaking':
				return '#22c55e'; // green
			default:
				return '#6b7280'; // gray
		}
	}

	get stateLabel(): string {
		switch (this.state) {
			case 'listening':
				return '듣는 중...';
			case 'processing':
				return '생각하는 중...';
			case 'speaking':
				return 'AI 응답 중...';
			default:
				return '대기';
		}
	}

	setListening() {
		this.state = 'listening';
	}
	setProcessing() {
		this.state = 'processing';
		this.interimText = '';
	}
	setSpeaking() {
		this.state = 'speaking';
	}
	setIdle() {
		// If mic is on, go to listening instead of idle
		if (this.micEnabled) {
			this.state = 'listening';
		} else {
			this.state = 'idle';
			this.interimText = '';
		}
	}
}

export const conversation = new ConversationStore();
