<script lang="ts">
	import { goto } from '$app/navigation';
	import { settings } from '$lib/stores/settings.svelte';
	import { registerDevice } from '$lib/api/register';

	let accessCode = $state('');
	let deviceName = $state('');
	let status = $state<'idle' | 'loading' | 'error'>('idle');
	let errorMsg = $state('');

	async function handleRegister() {
		if (!accessCode.trim() || !deviceName.trim()) return;

		status = 'loading';
		errorMsg = '';

		try {
			const result = await registerDevice(accessCode.trim(), deviceName.trim());
			settings.authToken = result.token;
			settings.deviceId = result.id;
			settings.deviceName = result.name;
			goto('/');
		} catch (err) {
			status = 'error';
			errorMsg = err instanceof Error ? err.message : '등록 실패';
		}
	}
</script>

<div class="flex flex-col h-screen bg-gray-950 text-white">
	<header class="flex items-center gap-3 px-4 py-3 bg-gray-900 border-b border-gray-800">
		<button onclick={() => goto('/settings')} class="p-2 rounded-lg hover:bg-gray-800 transition-colors">
			←
		</button>
		<span class="font-semibold text-lg">기기 등록</span>
	</header>

	<div class="flex-1 flex flex-col items-center justify-center px-6 gap-8">
		<div class="text-center">
			<span class="text-6xl">🦖</span>
			<p class="text-xl font-semibold mt-4">VoiceChat 기기 등록</p>
			<p class="text-gray-400 text-sm mt-2">서버에서 발급받은 등록 코드를 입력하세요</p>
		</div>

		<div class="w-full max-w-sm space-y-4">
			<div>
				<label for="device-name" class="block text-sm text-gray-400 mb-1">기기 이름</label>
				<input
					id="device-name"
					type="text"
					bind:value={deviceName}
					placeholder="예: 내 갤럭시"
					class="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
				/>
			</div>
			<div>
				<label for="access-code" class="block text-sm text-gray-400 mb-1">등록 코드</label>
				<input
					id="access-code"
					type="password"
					bind:value={accessCode}
					placeholder="서버 등록 코드"
					class="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
				/>
			</div>

			{#if errorMsg}
				<p class="text-red-400 text-sm text-center">{errorMsg}</p>
			{/if}

			<button
				onclick={handleRegister}
				disabled={!accessCode.trim() || !deviceName.trim() || status === 'loading'}
				class="w-full px-4 py-3 bg-blue-600 hover:bg-blue-500 disabled:bg-gray-700 disabled:text-gray-500 rounded-xl font-medium transition-colors"
			>
				{status === 'loading' ? '등록 중...' : '등록하기'}
			</button>
		</div>
	</div>
</div>
