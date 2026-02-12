<script lang="ts">
	import '../app.css';
	let { children } = $props();
</script>

<div class="min-h-screen bg-gray-950 text-white flex flex-col">
	{@render children()}
</div>
