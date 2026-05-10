/**
 * Ralph autonomous tasks API client - streams via /api/task SSE
 */
import { settings } from '$lib/stores/settings.svelte';
import { tasks, type Task } from '$lib/stores/tasks.svelte';

interface StartTaskOptions {
	prompt: string;
	mode?: 'ralph';
	maxIterations?: number;
	completionPromise?: string;
}

/**
 * Start a Ralph task. Returns the local task object (tracked in tasks store) and a cancel fn.
 * SSE events update the task in the store as they arrive.
 */
export function startTask(opts: StartTaskOptions): { localId: string; cancel: () => void } {
	const localId = `local_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
	const controller = new AbortController();

	const task: Task = {
		id: localId,
		prompt: opts.prompt,
		mode: opts.mode || 'ralph',
		status: 'queued',
		iteration: 0,
		maxIterations: opts.maxIterations || 30,
		progressMessages: [],
		artifacts: [],
		createdAt: Date.now(),
		cancel: () => controller.abort(),
	};
	tasks.add(task);

	(async () => {
		try {
			const res = await fetch(`${settings.serverUrl}/api/task`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					instanceId: settings.selectedInstance,
					mode: task.mode,
					prompt: opts.prompt,
					maxIterations: task.maxIterations,
					completionPromise: opts.completionPromise || 'DONE',
				}),
				signal: controller.signal,
			});

			if (!res.ok) {
				const errText = await res.text().catch(() => '');
				tasks.update(localId, { status: 'error', error: `HTTP ${res.status}: ${errText}`, completedAt: Date.now() });
				return;
			}
			if (!res.body) {
				tasks.update(localId, { status: 'error', error: '응답 본문 없음', completedAt: Date.now() });
				return;
			}

			tasks.update(localId, { status: 'running' });

			const reader = res.body.getReader();
			const decoder = new TextDecoder();
			let buf = '';
			let serverTaskId = '';

			while (true) {
				const { done, value } = await reader.read();
				if (done) break;
				buf += decoder.decode(value, { stream: true });
				const lines = buf.split('\n');
				buf = lines.pop() || '';

				for (const line of lines) {
					if (!line.startsWith('data: ')) continue;
					const data = line.slice(6);
					if (data === '[DONE]') return;
					let evt: any;
					try { evt = JSON.parse(data); } catch { continue; }
					switch (evt.type) {
						case 'init':
							serverTaskId = evt.taskId;
							tasks.update(localId, { id: localId }); // keep local id, server id stored elsewhere if needed
							break;
						case 'started':
							tasks.update(localId, { status: 'running' });
							break;
						case 'progress':
							tasks.update(localId, { iteration: evt.iteration || 0 });
							if (evt.message) tasks.appendProgress(localId, `[${evt.iteration}] ${evt.message}`);
							break;
						case 'log':
							if (evt.line) tasks.appendProgress(localId, evt.line);
							break;
						case 'done':
							tasks.update(localId, {
								status: 'done',
								summary: evt.summary,
								iteration: evt.iteration || 0,
								completedAt: Date.now(),
							});
							break;
						case 'error':
							tasks.update(localId, { status: 'error', error: evt.error, completedAt: Date.now() });
							break;
						case 'file':
							tasks.appendArtifact(localId, { name: evt.filename, url: evt.url, kind: 'file' });
							break;
					}
					void serverTaskId;
				}
			}
		} catch (err: any) {
			if (err?.name === 'AbortError') {
				tasks.update(localId, { status: 'cancelled', completedAt: Date.now() });
			} else {
				tasks.update(localId, { status: 'error', error: String(err?.message || err), completedAt: Date.now() });
			}
		}
	})();

	return { localId, cancel: () => controller.abort() };
}
