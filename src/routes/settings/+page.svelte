<script lang="ts">
	import { goto } from '$app/navigation';
	import { settings } from '$lib/stores/settings.svelte';
	import { checkServerHealth } from '$lib/api/health';

	let testStatus = $state<'idle' | 'testing' | 'ok' | 'error'>('idle');
	let testMessage = $state('');

	async function testConnection() {
		testStatus = 'testing';
		testMessage = '';
		const health = await checkServerHealth();
		if (health.ok) {
			testStatus = 'ok';
			testMessage = `연결 성공! (${health.latencyMs}ms, 인스턴스 ${health.instances ?? 0}개)`;
		} else {
			testStatus = 'error';
			testMessage = health.error || '연결 실패';
		}
	}
</script>

<div class="app-container bg-gray-950 text-white">
	<header class="flex-shrink-0 flex items-center gap-3 px-4 py-3 bg-gray-900 border-b border-gray-800">
		<button onclick={() => goto('/')} class="p-2 rounded-lg hover:bg-gray-800 transition-colors">
			←
		</button>
		<span class="font-semibold text-lg">설정</span>
	</header>

	<div class="flex-1 overflow-y-auto px-4 py-6 space-y-6">
		<!-- Server Settings -->
		<section>
			<h2 class="text-sm font-medium text-gray-400 uppercase tracking-wider mb-3">🔗 서버 설정</h2>
			<div class="space-y-4 bg-gray-900 rounded-xl p-4">
				<div>
					<label for="server-url" class="block text-sm text-gray-400 mb-1">서버 URL</label>
					<input
						id="server-url"
						type="url"
						bind:value={settings.serverUrl}
						placeholder="https://voicechat.example.com"
						class="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
					/>
					<p class="text-xs text-gray-500 mt-1">VoiceChat 중계 서버 주소</p>
				</div>
				<div>
					<label for="auth-token" class="block text-sm text-gray-400 mb-1">인증 토큰</label>
					<input
						id="auth-token"
						type="password"
						bind:value={settings.authToken}
						placeholder="AUTH_TOKEN"
						class="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
					/>
				</div>
				<button
					onclick={testConnection}
					disabled={testStatus === 'testing'}
					class="w-full px-4 py-2 rounded-lg font-medium transition-colors
						{testStatus === 'testing' ? 'bg-gray-700 text-gray-400' :
						 testStatus === 'ok' ? 'bg-green-700 text-white' :
						 testStatus === 'error' ? 'bg-red-700 text-white' :
						 'bg-blue-600 hover:bg-blue-500 text-white'}"
				>
					{#if testStatus === 'testing'}
						연결 테스트 중...
					{:else if testStatus === 'ok'}
						✅ {testMessage}
					{:else if testStatus === 'error'}
						❌ {testMessage}
					{:else}
						연결 테스트
					{/if}
				</button>
			</div>
		</section>

		<!-- Voice Settings -->
		<section>
			<h2 class="text-sm font-medium text-gray-400 uppercase tracking-wider mb-3">🔊 음성 출력</h2>
			<div class="space-y-3 bg-gray-900 rounded-xl p-4">
				<div class="flex justify-between items-center">
					<span>TTS 엔진</span>
					<select
						bind:value={settings.ttsEngine}
						class="bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-white"
					>
						<option value="webspeech">Web Speech API</option>
						<option value="elevenlabs" disabled>ElevenLabs (준비중)</option>
					</select>
				</div>
			</div>
		</section>

		<!-- Input Settings -->
		<section>
			<h2 class="text-sm font-medium text-gray-400 uppercase tracking-wider mb-3">🎤 음성 입력</h2>
			<div class="space-y-3 bg-gray-900 rounded-xl p-4">
				<div class="flex justify-between items-center">
					<span>STT 엔진</span>
					<select
						bind:value={settings.sttEngine}
						class="bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-white"
					>
						<option value="webspeech">Web Speech API</option>
						<option value="deepgram" disabled>Deepgram (준비중)</option>
					</select>
				</div>
				<div class="flex justify-between items-center">
					<span>언어</span>
					<select
						bind:value={settings.language}
						class="bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-white"
					>
						<option value="ko-KR">한국어</option>
						<option value="en-US">English</option>
						<option value="ja-JP">日本語</option>
					</select>
				</div>
			</div>
		</section>

		<!-- Info -->
		<section>
			<div class="bg-gray-900/50 rounded-xl p-4 text-sm text-gray-500">
				<p>🦖 VoiceChat v0.2</p>
				<p>VoiceChat Server → ClawBridge → OpenClaw</p>
			</div>
		</section>
	</div>
</div>
