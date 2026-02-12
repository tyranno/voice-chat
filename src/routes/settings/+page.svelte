<script lang="ts">
	import { goto } from '$app/navigation';
</script>

<div class="flex flex-col h-screen">
	<!-- Header -->
	<header class="flex items-center gap-3 px-4 py-3 bg-gray-900 border-b border-gray-800">
		<button onclick={() => goto('/')} class="p-2 rounded-lg hover:bg-gray-800 transition-colors">
			←
		</button>
		<span class="font-semibold text-lg">설정</span>
	</header>

	<div class="flex-1 overflow-y-auto px-4 py-6 space-y-6">
		<!-- Voice Settings -->
		<section>
			<h2 class="text-sm font-medium text-gray-400 uppercase tracking-wider mb-3">🔊 음성 설정</h2>
			<div class="space-y-3 bg-gray-900 rounded-xl p-4">
				<div class="flex justify-between items-center">
					<span>TTS 엔진</span>
					<span class="text-gray-500">ElevenLabs (Phase 4)</span>
				</div>
				<div class="flex justify-between items-center">
					<span>음성</span>
					<span class="text-gray-500">미설정</span>
				</div>
			</div>
		</section>

		<!-- Input Settings -->
		<section>
			<h2 class="text-sm font-medium text-gray-400 uppercase tracking-wider mb-3">🎤 입력 설정</h2>
			<div class="space-y-3 bg-gray-900 rounded-xl p-4">
				<div class="flex justify-between items-center">
					<span>STT 엔진</span>
					<span class="text-gray-500">Deepgram (Phase 3)</span>
				</div>
				<div class="flex justify-between items-center">
					<span>언어</span>
					<span class="text-gray-500">한국어</span>
				</div>
			</div>
		</section>

		<!-- Server Settings -->
		<section>
			<h2 class="text-sm font-medium text-gray-400 uppercase tracking-wider mb-3">🔗 서버 설정</h2>
			<div class="space-y-3 bg-gray-900 rounded-xl p-4">
				<div class="flex justify-between items-center">
					<span>Gateway</span>
					<span class="text-gray-500">localhost:18789</span>
				</div>
				<div class="flex justify-between items-center">
					<span>상태</span>
					<span class="text-green-400">연결됨 ✓</span>
				</div>
			</div>
		</section>
	</div>
</div>
