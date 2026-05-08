<script lang="ts">
	import { goto } from '$app/navigation';
	import { onMount, onDestroy } from 'svelte';
	import { Capacitor } from '@capacitor/core';
	import { settings } from '$lib/stores/settings.svelte';
	import { checkServerHealth } from '$lib/api/health';

	let step = $state<1 | 2 | 3>(1);
	let serverInput = $state(settings.serverUrl);
	let testStatus = $state<'idle' | 'testing' | 'ok' | 'error'>('idle');
	let testMessage = $state('');
	let micPermission = $state<'unknown' | 'granted' | 'denied'>('unknown');

	async function requestMic() {
		try {
			if (Capacitor.isNativePlatform()) {
				const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
				stream.getTracks().forEach((t) => t.stop());
				micPermission = 'granted';
			} else {
				const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
				stream.getTracks().forEach((t) => t.stop());
				micPermission = 'granted';
			}
		} catch {
			micPermission = 'denied';
		}
	}

	async function testServer() {
		settings.serverUrl = serverInput.trim();
		testStatus = 'testing';
		testMessage = '';
		const r = await checkServerHealth();
		if (r.ok) {
			testStatus = 'ok';
			testMessage = `연결 성공 (${r.latencyMs}ms, 인스턴스 ${r.instances ?? 0}개)`;
		} else {
			testStatus = 'error';
			testMessage = r.error || '연결 실패';
		}
	}

	function finish() {
		settings.onboardingDone = true;
		goto('/');
	}

	function onBack() { goto('/'); }
	onMount(() => window.addEventListener('hardwareBackPress', onBack));
	onDestroy(() => window.removeEventListener('hardwareBackPress', onBack));
</script>

<div class="app-container bg-gray-950 text-white">
	<header class="flex-shrink-0 px-4 py-3 flex items-center justify-between">
		<span class="text-sm text-gray-500">단계 {step} / 3</span>
		{#if step < 3}
			<button onclick={finish} class="text-xs text-gray-500 hover:text-gray-300 transition-colors">건너뛰기</button>
		{/if}
	</header>

	<div class="flex-1 overflow-y-auto px-6 py-6 flex flex-col items-center justify-center text-center gap-6">
		{#if step === 1}
			<span class="text-7xl">🦖</span>
			<h1 class="text-3xl font-bold">Rex에 오신 것을 환영합니다</h1>
			<p class="text-gray-400 text-base leading-relaxed max-w-sm">
				마이크 한 번이면<br/>
				Rex가 듣고, 답하고, 일하고, 조언합니다.
			</p>
			<p class="text-xs text-gray-600 max-w-sm">
				음성 대화 · 자율 작업 · 음악 재생 · 파일 받기 — 모두 한 화면에서.
			</p>
		{:else if step === 2}
			<span class="text-6xl">🎙️</span>
			<h2 class="text-2xl font-bold">권한이 필요합니다</h2>
			<p class="text-gray-400 max-w-sm">
				음성 대화를 위해 마이크 권한이 필요합니다.<br/>
				알림 권한은 백그라운드 응답을 받는 데 사용합니다.
			</p>

			<div class="w-full max-w-sm bg-gray-900 rounded-xl p-4 space-y-3">
				<div class="flex items-center justify-between">
					<span class="text-sm">마이크</span>
					{#if micPermission === 'granted'}
						<span class="text-xs text-emerald-400">✅ 허용됨</span>
					{:else if micPermission === 'denied'}
						<span class="text-xs text-red-400">❌ 거부됨 — OS 설정에서 허용</span>
					{:else}
						<button onclick={requestMic} class="px-3 py-1.5 text-xs bg-emerald-500 hover:bg-emerald-400 rounded-lg transition-colors">권한 요청</button>
					{/if}
				</div>
			</div>

			{#if micPermission === 'denied'}
				<p class="text-xs text-gray-500 max-w-sm">
					마이크 없이도 텍스트로 사용 가능합니다.
				</p>
			{/if}
		{:else}
			<span class="text-6xl">🔗</span>
			<h2 class="text-2xl font-bold">서버 연결</h2>
			<p class="text-gray-400 text-sm max-w-sm">
				기본 서버(<code class="text-gray-300">voicechat.tyranno.xyz</code>)를 그대로 사용해도 됩니다.
			</p>
			<div class="w-full max-w-sm space-y-3">
				<input
					type="url"
					bind:value={serverInput}
					placeholder="https://voicechat.example.com"
					class="w-full px-4 py-3 bg-gray-900 border border-gray-700 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-emerald-500"
				/>
				<button
					onclick={testServer}
					disabled={testStatus === 'testing'}
					class="w-full px-4 py-3 rounded-xl font-medium transition-colors
						{testStatus === 'testing' ? 'bg-gray-700 text-gray-400' :
						 testStatus === 'ok' ? 'bg-emerald-600 text-white' :
						 testStatus === 'error' ? 'bg-red-600 text-white' :
						 'bg-gray-700 hover:bg-gray-600 text-white'}"
				>
					{#if testStatus === 'testing'}연결 테스트 중...
					{:else if testStatus === 'ok'}✅ {testMessage}
					{:else if testStatus === 'error'}❌ {testMessage}
					{:else}연결 테스트{/if}
				</button>
			</div>
		{/if}
	</div>

	<footer class="flex-shrink-0 px-6 py-6 flex gap-3" style="padding-bottom: max(1.5rem, env(safe-area-inset-bottom));">
		{#if step > 1}
			<button
				onclick={() => step = (step - 1) as 1 | 2}
				class="px-5 py-3 bg-gray-800 hover:bg-gray-700 rounded-xl font-medium transition-colors"
			>이전</button>
		{/if}
		{#if step < 3}
			<button
				onclick={() => step = (step + 1) as 2 | 3}
				class="flex-1 px-5 py-3 bg-emerald-500 hover:bg-emerald-400 rounded-xl font-medium transition-colors"
			>다음</button>
		{:else}
			<button
				onclick={finish}
				class="flex-1 px-5 py-3 bg-emerald-500 hover:bg-emerald-400 rounded-xl font-medium transition-colors"
			>시작하기 →</button>
		{/if}
	</footer>
</div>
