/**
 * Toast 알림 store - 일시 표시되는 짧은 메시지
 */

export type ToastKind = 'info' | 'success' | 'warning' | 'error';

export interface Toast {
	id: number;
	kind: ToastKind;
	message: string;
	durationMs: number;
}

class ToastStore {
	#toasts: Toast[] = $state([]);
	#nextId = 1;

	get toasts() { return this.#toasts; }

	show(kind: ToastKind, message: string, durationMs = 3500) {
		const id = this.#nextId++;
		this.#toasts = [...this.#toasts, { id, kind, message, durationMs }];
		if (durationMs > 0) {
			setTimeout(() => this.dismiss(id), durationMs);
		}
		return id;
	}

	info(msg: string, durationMs?: number) { return this.show('info', msg, durationMs); }
	success(msg: string, durationMs?: number) { return this.show('success', msg, durationMs); }
	warning(msg: string, durationMs?: number) { return this.show('warning', msg, durationMs); }
	error(msg: string, durationMs?: number) { return this.show('error', msg, durationMs ?? 5000); }

	dismiss(id: number) {
		this.#toasts = this.#toasts.filter((t) => t.id !== id);
	}

	clear() { this.#toasts = []; }
}

export const toast = new ToastStore();
