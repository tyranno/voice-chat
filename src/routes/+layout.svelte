<script lang="ts">
	import '../app.css';
	import { onMount } from 'svelte';
	import ToastContainer from '$lib/components/ToastContainer.svelte';
	import { toast } from '$lib/stores/toast.svelte';

	let { children } = $props();
	let globalError = $state('');

	onMount(() => {
		window.addEventListener('error', (e) => {
			globalError = `JS Error: ${e.message} at ${e.filename}:${e.lineno}`;
			toast.error(`오류: ${e.message}`);
		});
		window.addEventListener('unhandledrejection', (e) => {
			globalError = `Promise Error: ${e.reason}`;
			toast.error(`오류: ${e.reason}`);
		});
	});
</script>

<div class="min-h-screen bg-gray-950 text-white flex flex-col">
	{#if globalError}
		<div class="bg-red-900 text-red-200 text-xs p-2 font-mono break-all">
			⚠️ {globalError}
		</div>
	{/if}
	{@render children()}
	<ToastContainer />
</div>
