<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { goto } from '$app/navigation';
	import { settings } from '$lib/stores/settings.svelte';
	import { toast } from '$lib/stores/toast.svelte';

	function onBackPress() { goto('/'); }
	onMount(() => window.addEventListener('hardwareBackPress', onBackPress));
	onDestroy(() => window.removeEventListener('hardwareBackPress', onBackPress));
	import { checkServerHealth } from '$lib/api/health';
	import { checkForUpdate, downloadAndInstall, type ApkInfo } from '$lib/api/updater';

	let micPermission = $state<'unknown' | 'granted' | 'denied'>('unknown');
	onMount(async () => {
		try {
			const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
			stream.getTracks().forEach((t) => t.stop());
			micPermission = 'granted';
		} catch {
			micPermission = 'denied';
		}
	});

	async function requestMic() {
		try {
			const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
			stream.getTracks().forEach((t) => t.stop());
			micPermission = 'granted';
			toast.success('마이크 권한 허용됨');
		} catch {
			micPermission = 'denied';
			toast.warning('마이크 권한이 거부되었습니다. OS 설정에서 변경하세요.');
		}
	}

	function restartOnboarding() {
		settings.onboardingDone = false;
		goto('/onboarding');
	}

	let testStatus = $state<'idle' | 'testing' | 'ok' | 'error'>('idle');
	let testMessage = $state('');

	let updateStatus = $state<'idle' | 'checking' | 'available' | 'downloading' | 'done' | 'error'>('idle');
	let updateInfo = $state<ApkInfo | null>(null);
	let updateError = $state('');
	let downloadProgress = $state(0);

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

	async function onCheckUpdate() {
		updateStatus = 'checking';
		updateError = '';
		const result = await checkForUpdate();
		if (result.available && result.info) {
			updateStatus = 'available';
			updateInfo = result.info;
		} else {
			updateStatus = 'error';
			updateError = result.error || '업데이트 없음';
		}
	}

	async function onDownloadInstall() {
		updateStatus = 'downloading';
		downloadProgress = 0;
		const result = await downloadAndInstall((percent) => {
			downloadProgress = percent;
		});
		if (result.success) {
			updateStatus = 'done';
		} else {
			updateStatus = 'error';
			updateError = result.error || '설치 실패';
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
				</div>
				<button
					onclick={testConnection}
					disabled={testStatus === 'testing'}
					class="w-full px-4 py-2 rounded-lg font-medium transition-colors
						{testStatus === 'testing' ? 'bg-gray-700 text-gray-400' :
						 testStatus === 'ok' ? 'bg-green-700 text-white' :
						 testStatus === 'error' ? 'bg-red-700 text-white' :
						 'bg-emerald-500 hover:bg-emerald-400 text-white'}"
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
						<option value="native">네이티브 (Samsung/Google TTS)</option>
						<option value="webspeech">Web Speech API</option>
						<option value="elevenlabs" disabled>ElevenLabs (준비중)</option>
					</select>
				</div>
				<p class="text-xs text-gray-500">네이티브: 폰 설정의 기본 TTS 엔진 사용 (Samsung TTS 등)</p>
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
						<option value="vosk">VOSK (서버 스트리밍)</option>
						<option value="webspeech">Web Speech API</option>
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

		<!-- App Update -->
		<section>
			<h2 class="text-sm font-medium text-gray-400 uppercase tracking-wider mb-3">📦 앱 업데이트</h2>
			<div class="space-y-3 bg-gray-900 rounded-xl p-4">
				{#if updateStatus === 'downloading'}
					<div class="space-y-2">
						<div class="flex justify-between text-sm">
							<span>다운로드 중...</span>
							<span>{downloadProgress}%</span>
						</div>
						<div class="w-full bg-gray-700 rounded-full h-2">
							<div class="bg-blue-500 h-2 rounded-full transition-all" style="width: {downloadProgress}%"></div>
						</div>
					</div>
				{:else if updateStatus === 'available' && updateInfo}
					<div class="text-sm space-y-1">
						<p>새 버전: <span class="text-green-400 font-medium">v{updateInfo.version}</span></p>
						<p class="text-gray-500">크기: {(updateInfo.size / 1024 / 1024).toFixed(1)} MB</p>
					</div>
					<button
						onclick={onDownloadInstall}
						class="w-full px-4 py-2 rounded-lg font-medium bg-emerald-500 hover:bg-emerald-400 text-white transition-colors"
					>
						⬇️ 다운로드 & 설치
					</button>
				{:else if updateStatus === 'error'}
					<p class="text-sm text-red-400">{updateError}</p>
				{:else if updateStatus === 'done'}
					<p class="text-sm text-green-400">✅ 설치 화면이 열렸습니다</p>
				{/if}

				{#if updateStatus !== 'downloading'}
					<button
						onclick={onCheckUpdate}
						disabled={updateStatus === 'checking'}
						class="w-full px-4 py-2 rounded-lg font-medium transition-colors
							{updateStatus === 'checking' ? 'bg-gray-700 text-gray-400' : 'bg-emerald-500 hover:bg-emerald-400 text-white'}"
					>
						{updateStatus === 'checking' ? '확인 중...' : '🔄 업데이트 확인'}
					</button>
				{/if}
			</div>
		</section>

		<!-- Permissions -->
		<section>
			<h2 class="text-sm font-medium text-gray-400 uppercase tracking-wider mb-3">🔐 권한</h2>
			<div class="space-y-3 bg-gray-900 rounded-xl p-4">
				<div class="flex items-center justify-between">
					<div>
						<p class="text-sm">마이크</p>
						<p class="text-xs text-gray-500">음성 입력에 필요</p>
					</div>
					{#if micPermission === 'granted'}
						<span class="text-xs text-emerald-400">✅ 허용됨</span>
					{:else if micPermission === 'denied'}
						<span class="text-xs text-red-400">❌ 거부됨</span>
					{:else}
						<button onclick={requestMic} class="px-3 py-1.5 text-xs bg-emerald-500 hover:bg-emerald-400 rounded-lg transition-colors">권한 요청</button>
					{/if}
				</div>
				{#if micPermission === 'denied'}
					<p class="text-xs text-gray-500">
						OS 설정 → 앱 → Rex → 권한에서 마이크를 허용해주세요.
					</p>
				{/if}
			</div>
		</section>

		<!-- Developer Mode -->
		<section>
			<h2 class="text-sm font-medium text-gray-400 uppercase tracking-wider mb-3">🛠 개발자</h2>
			<div class="space-y-3 bg-gray-900 rounded-xl p-4">
				<div class="flex items-center justify-between">
					<div>
						<p class="text-sm">개발자 모드</p>
						<p class="text-xs text-gray-500">실시간 디버그 로그 표시</p>
					</div>
					<label class="relative inline-flex items-center cursor-pointer">
						<input type="checkbox" bind:checked={settings.developerMode} class="sr-only peer" />
						<div class="w-11 h-6 bg-gray-700 rounded-full peer peer-checked:bg-emerald-500 transition-colors after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-transform peer-checked:after:translate-x-5"></div>
					</label>
				</div>
				<button
					onclick={restartOnboarding}
					class="w-full px-4 py-2 rounded-lg font-medium bg-gray-700 hover:bg-gray-600 text-white transition-colors text-sm"
				>
					온보딩 다시 보기
				</button>
			</div>
		</section>

		<!-- Info -->
		<section>
			<div class="bg-gray-900/50 rounded-xl p-4 text-sm text-gray-500">
				<p>🦖 Rex v0.3</p>
				<p>App → GCP Server → ClawBridge → OpenClaw</p>
			</div>
		</section>
	</div>
</div>
