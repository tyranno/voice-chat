package com.tyranokim.voicechat.audio;

import android.net.Uri;
import android.util.Log;

import androidx.annotation.Nullable;

import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.Locale;

/**
 * Resolves YouTube watch URLs to playable audio stream URLs via the voicechat server (yt-dlp).
 *
 * Piped was removed: Piped API instances are DNS-blocked in Korea, making them unreliable.
 * All resolution is now done server-side via yt-dlp, which handles both VOD and live streams.
 *
 * Flow:
 *  - YouTube URL → GET /api/youtube/stream?videoId=xxx
 *  - If isLive=true  → /api/youtube/hls-proxy?videoId=xxx  (server rewrites HLS manifest + proxies segments)
 *  - If isLive=false → audioUrl directly (yt-dlp n-sig makes VOD URLs non-IP-bound)
 */
public class StreamUrlResolver {
    private static final String TAG = "StreamUrlResolver";

    private static final String SERVER_BASE       = "https://voicechat.tyranno.xyz";
    private static final String SERVER_STREAM_API = SERVER_BASE + "/api/youtube/stream?videoId=";
    private static final String SERVER_HLS_PROXY  = SERVER_BASE + "/api/youtube/hls-proxy?videoId=";
    private static final String SERVER_PROXY      = SERVER_BASE + "/api/youtube/proxy?videoId=";

    /** Timeout for the server /api/youtube/stream call (yt-dlp can take 30-40s). */
    private static final int SERVER_TIMEOUT_MS = 60_000;

    public static final class ResolveResult {
        public final boolean ok;
        public final String playableUrl;
        public final String sourceType;
        public final String message;

        ResolveResult(boolean ok, @Nullable String playableUrl, String sourceType, @Nullable String message) {
            this.ok = ok;
            this.playableUrl = playableUrl;
            this.sourceType = sourceType;
            this.message = message;
        }
    }

    public ResolveResult resolve(String sourceUrl, @Nullable String playableUrlHint) {
        String sourceType = classify(sourceUrl);

        // If a pre-resolved playable URL was provided and it's usable, use it directly
        if (isNonEmpty(playableUrlHint)) {
            String hintedType = classify(playableUrlHint);
            if (!"youtube_page".equals(hintedType) && !"empty".equals(hintedType)) {
                return new ResolveResult(true, playableUrlHint, hintedType, null);
            }
        }

        // For YouTube URLs, resolve via server yt-dlp
        if ("youtube_page".equals(sourceType)) {
            String videoId = extractVideoId(sourceUrl);
            if (videoId == null) {
                return new ResolveResult(false, null, sourceType, "Cannot extract videoId from: " + sourceUrl);
            }
            return resolveViaServer(videoId);
        }

        // Direct URL — pass through
        return new ResolveResult(true, sourceUrl, sourceType, null);
    }

    /** Resolve a videoId by calling the server's yt-dlp endpoint. */
    public ResolveResult resolveVideoId(String videoId) {
        return resolveViaServer(videoId);
    }

    /**
     * Call /api/youtube/stream?videoId={id} to resolve stream info via server-side yt-dlp.
     * Returns HLS proxy URL for live streams, direct audioUrl for VOD.
     */
    private ResolveResult resolveViaServer(String videoId) {
        try {
            String apiUrl = SERVER_STREAM_API + videoId;
            Log.d(TAG, "Resolving via server: " + apiUrl);

            URL url = new URL(apiUrl);
            HttpURLConnection conn = (HttpURLConnection) url.openConnection();
            conn.setRequestMethod("GET");
            conn.setConnectTimeout(SERVER_TIMEOUT_MS);
            conn.setReadTimeout(SERVER_TIMEOUT_MS);
            conn.setRequestProperty("User-Agent", "VoiceChat-Android/1.0");

            int code = conn.getResponseCode();
            if (code != 200) {
                conn.disconnect();
                Log.w(TAG, "Server returned HTTP " + code + " for videoId=" + videoId);
                // Fallback: use proxy directly (server will handle it, might still fail for live)
                return new ResolveResult(true, SERVER_PROXY + videoId, "http", null);
            }

            BufferedReader reader = new BufferedReader(new InputStreamReader(conn.getInputStream()));
            StringBuilder sb = new StringBuilder();
            String line;
            while ((line = reader.readLine()) != null) sb.append(line);
            reader.close();
            conn.disconnect();

            JSONObject data = new JSONObject(sb.toString());
            boolean isLive   = data.optBoolean("isLive", false);
            String audioUrl  = data.optString("audioUrl", "");
            String title     = data.optString("title", videoId);

            // Also detect live by URL pattern in case yt-dlp didn't report is_live correctly
            if (!isLive && (audioUrl.contains("manifest.googlevideo.com") || audioUrl.contains(".m3u8"))) {
                isLive = true;
                Log.d(TAG, "Live detected from audioUrl pattern for " + videoId);
            }

            if (isLive) {
                // Live stream: use HLS proxy (server proxies manifest + all IP-bound segments)
                // Server pre-warms the HLS cache when /stream is called, so first manifest fetch is fast
                String hlsProxyUrl = SERVER_HLS_PROXY + videoId;
                Log.i(TAG, "Live stream " + videoId + " → HLS proxy: " + hlsProxyUrl);
                return new ResolveResult(true, hlsProxyUrl, "hls", null);
            } else {
                // VOD: use server proxy (proven working, avoids any IP-binding uncertainty)
                String proxyUrl = SERVER_PROXY + videoId;
                Log.i(TAG, "VOD " + videoId + " → proxy: " + proxyUrl);
                return new ResolveResult(true, proxyUrl, "http", null);
            }

        } catch (Exception e) {
            Log.e(TAG, "Server resolve failed for " + videoId + ": " + e.getMessage());
            // Last resort: use proxy directly
            return new ResolveResult(true, SERVER_PROXY + videoId, "http", null);
        }
    }

    @Nullable
    private String extractVideoId(String url) {
        try {
            Uri uri = Uri.parse(url);
            // youtube.com/watch?v=xxx
            String v = uri.getQueryParameter("v");
            if (isNonEmpty(v)) return v;
            // youtu.be/xxx
            String path = uri.getPath();
            if (path != null && path.length() > 1) return path.substring(1);
        } catch (Exception ignored) {}
        return null;
    }

    public String classify(@Nullable String url) {
        if (!isNonEmpty(url)) return "empty";
        String lower = url.toLowerCase(Locale.US);
        if (lower.startsWith("file://")) return "file";
        if (lower.startsWith("content://")) return "content";
        Uri uri = Uri.parse(url);
        String host = uri.getHost() != null ? uri.getHost().toLowerCase(Locale.US) : "";
        String path = uri.getPath() != null ? uri.getPath().toLowerCase(Locale.US) : "";
        if (host.contains("youtube.com") || host.contains("youtu.be")) return "youtube_page";
        if (path.endsWith(".m3u8") || lower.contains("/hls-proxy")) return "hls";
        if (path.endsWith(".mpd")) return "dash";
        if (path.endsWith(".mp3") || path.endsWith(".m4a") || path.endsWith(".aac")
                || path.endsWith(".ogg") || path.endsWith(".wav") || path.endsWith(".flac")) {
            return "audio_file";
        }
        if (lower.startsWith("http://") || lower.startsWith("https://")) return "http";
        return "unknown";
    }

    private boolean isNonEmpty(@Nullable String value) {
        return value != null && !value.trim().isEmpty();
    }
}
