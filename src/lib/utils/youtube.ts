/**
 * YouTube URL 파싱 유틸리티
 */

/** YouTube 영상 ID 추출 (다양한 URL 형식 지원) */
export function extractVideoId(url: string): string | null {
	const patterns = [
		/(?:youtube\.com\/watch\?.*v=|youtu\.be\/|youtube\.com\/embed\/|youtube\.com\/shorts\/)([a-zA-Z0-9_-]{11})/,
	];
	for (const p of patterns) {
		const m = url.match(p);
		if (m) return m[1];
	}
	return null;
}

/** 텍스트에서 모든 YouTube 영상 ID 추출 */
export function extractAllVideoIds(text: string): string[] {
	const regex = /(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/watch\?[^\s]*v=|youtu\.be\/|youtube\.com\/embed\/|youtube\.com\/shorts\/)([a-zA-Z0-9_-]{11})/g;
	const ids: string[] = [];
	let m: RegExpExecArray | null;
	while ((m = regex.exec(text)) !== null) {
		if (!ids.includes(m[1])) ids.push(m[1]);
	}
	return ids;
}

/** 텍스트에 YouTube 링크가 포함되어 있는지 확인 */
export function hasYouTubeLink(text: string): boolean {
	return extractAllVideoIds(text).length > 0;
}
