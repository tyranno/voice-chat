<script lang="ts">
	/**
	 * YouTube IFrame 미니 플레이어 컴포넌트
	 * - 하단 고정, 채팅과 동시 사용 가능
	 * - 플레이/일시정지/정지/닫기 컨트롤
	 */

	interface Props {
		videoId: string;
		onclose?: () => void;
		/** TTS 일시정지 콜백 (YouTube 재생 시) */
		onplay?: () => void;
		/** TTS 재개 콜백 (YouTube 정지 시) */
		onpause?: () => void;
	}

	let { videoId, onclose, onplay, onpause }: Props = $props();

	let playerEl: HTMLDivElement;
	let player: any = $state(null);
	let isPlaying = $state(false);
	let title = $state('');
	let ready = $state(false);

	// YouTube IFrame API 로드
	function loadYouTubeAPI(): Promise<void> {
		return new Promise((resolve) => {
			if ((window as any).YT?.Player) {
				resolve();
				return;
			}
			// 이미 스크립트 로딩 중이면 콜백만 등록
			if (document.querySelector('script[src*="youtube.com/iframe_api"]')) {
				const prev = (window as any).onYouTubeIframeAPIReady;
				(window as any).onYouTubeIframeAPIReady = () => {
					prev?.();
					resolve();
				};
				return;
			}
			(window as any).onYouTubeIframeAPIReady = () => resolve();
			const tag = document.createElement('script');
			tag.src = 'https://www.youtube.com/iframe_api';
			document.head.appendChild(tag);
		});
	}

	async function initPlayer(id: string) {
		await loadYouTubeAPI();
		
		// 기존 플레이어 제거
		if (player) {
			try { player.destroy(); } catch {}
			player = null;
		}
		ready = false;

		// 컨테이너 안에 div 생성
		if (!playerEl) return;
		playerEl.innerHTML = '<div id="yt-player-inner"></div>';

		player = new (window as any).YT.Player('yt-player-inner', {
			height: '100%',
			width: '100%',
			videoId: id,
			playerVars: {
				autoplay: 1,
				playsinline: 1,
				rel: 0,
				modestbranding: 1,
				controls: 0,
				fs: 0,
			},
			events: {
				onReady: (e: any) => {
					ready = true;
					isPlaying = true;
					title = e.target.getVideoData()?.title || '';
					onplay?.();
				},
				onStateChange: (e: any) => {
					const YT = (window as any).YT;
					if (e.data === YT.PlayerState.PLAYING) {
						isPlaying = true;
						onplay?.();
					} else if (e.data === YT.PlayerState.PAUSED || e.data === YT.PlayerState.ENDED) {
						isPlaying = false;
						onpause?.();
					}
				}
			}
		});
	}

	// videoId 변경 시 재생성
	$effect(() => {
		if (videoId) {
			initPlayer(videoId);
		}
	});

	function togglePlay() {
		if (!player) return;
		if (isPlaying) {
			player.pauseVideo();
		} else {
			player.playVideo();
		}
	}

	function handleClose() {
		if (player) {
			try { player.destroy(); } catch {}
			player = null;
		}
		isPlaying = false;
		onpause?.();
		onclose?.();
	}
</script>

<!-- 미니 플레이어 (하단 고정) -->
<div class="bg-gray-900 border-t border-gray-800 px-3 py-2">
	<!-- 숨겨진 IFrame (오디오만 재생) -->
	<div bind:this={playerEl} class="w-0 h-0 overflow-hidden absolute"></div>
	
	<div class="flex items-center gap-3">
		<!-- 썸네일 -->
		<img
			src="https://img.youtube.com/vi/{videoId}/default.jpg"
			alt="thumbnail"
			class="w-12 h-9 rounded object-cover flex-shrink-0"
		/>
		
		<!-- 제목 -->
		<div class="flex-1 min-w-0">
			<p class="text-sm text-white truncate">{title || '로딩 중...'}</p>
			<p class="text-xs text-gray-500">YouTube</p>
		</div>
		
		<!-- 컨트롤 -->
		<div class="flex items-center gap-1 flex-shrink-0">
			<button
				onclick={togglePlay}
				disabled={!ready}
				class="w-9 h-9 flex items-center justify-center rounded-full bg-gray-800 hover:bg-gray-700 text-white transition-colors disabled:opacity-40"
			>
				{isPlaying ? '⏸' : '▶️'}
			</button>
			<button
				onclick={handleClose}
				class="w-9 h-9 flex items-center justify-center rounded-full bg-gray-800 hover:bg-gray-700 text-gray-400 hover:text-white transition-colors"
			>
				✕
			</button>
		</div>
	</div>
</div>
