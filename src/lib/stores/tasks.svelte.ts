/**
 * Ralph autonomous tasks store
 */

export type TaskStatus = 'queued' | 'running' | 'done' | 'error' | 'cancelled';

export interface TaskArtifact {
	name: string;
	url: string;
	kind?: string;
}

export interface Task {
	id: string;
	prompt: string;
	mode: 'ralph';
	status: TaskStatus;
	iteration: number;
	maxIterations: number;
	progressMessages: string[]; // latest 10
	summary?: string;
	error?: string;
	artifacts: TaskArtifact[];
	createdAt: number;
	completedAt?: number;
	cancel?: () => void;
}

class TasksStore {
	#tasks: Task[] = $state([]);

	get tasks() { return this.#tasks; }
	get active() { return this.#tasks.filter((t) => t.status === 'running' || t.status === 'queued'); }

	add(t: Task) {
		this.#tasks = [t, ...this.#tasks].slice(0, 50); // cap history
	}

	update(id: string, patch: Partial<Task>) {
		this.#tasks = this.#tasks.map((t) => (t.id === id ? { ...t, ...patch } : t));
	}

	appendProgress(id: string, msg: string) {
		this.#tasks = this.#tasks.map((t) => {
			if (t.id !== id) return t;
			const next = [...t.progressMessages, msg].slice(-10);
			return { ...t, progressMessages: next };
		});
	}

	appendArtifact(id: string, a: TaskArtifact) {
		this.#tasks = this.#tasks.map((t) =>
			t.id === id ? { ...t, artifacts: [...t.artifacts, a] } : t
		);
	}

	get(id: string) {
		return this.#tasks.find((t) => t.id === id);
	}

	clearFinished() {
		this.#tasks = this.#tasks.filter((t) => t.status === 'running' || t.status === 'queued');
	}
}

export const tasks = new TasksStore();
