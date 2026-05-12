package com.tyranokim.voicechat.audio;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.Service;
import android.content.Intent;
import android.content.pm.ServiceInfo;
import android.os.Build;
import android.os.Handler;
import android.os.IBinder;
import android.os.Looper;
import android.util.Log;

import androidx.annotation.Nullable;
import androidx.core.app.NotificationCompat;
import androidx.media3.common.AudioAttributes;
import androidx.media3.common.C;
import androidx.media3.common.MediaItem;
import androidx.media3.common.MimeTypes;
import androidx.media3.common.PlaybackException;
import androidx.media3.common.PlaybackParameters;
import androidx.media3.common.Player;
import androidx.media3.common.util.UnstableApi;
import androidx.media3.datasource.DefaultDataSource;
import androidx.media3.datasource.DefaultHttpDataSource;
import androidx.media3.exoplayer.ExoPlayer;
import androidx.media3.exoplayer.source.DefaultMediaSourceFactory;
import androidx.media3.session.MediaSession;
import androidx.media3.session.MediaStyleNotificationHelper;

import com.tyranokim.voicechat.R;

import org.json.JSONArray;

import java.util.ArrayList;
import java.util.List;

@UnstableApi
public class BackgroundAudioService extends Service {
    private static final String TAG = "BgAudioService";
    private static final String CHANNEL_ID = "background_audio_channel";
    private static final int NOTIFICATION_ID = 14001;

    private ExoPlayer player;
    private MediaSession mediaSession;
    // Raw playlist (YouTube watch URLs / other) — resolved lazily.
    private final List<String> rawPlaylist = new ArrayList<>();
    // Sparse cache of resolved playable URLs by index. null = not yet resolved.
    private final List<String> resolvedCache = new ArrayList<>();
    private final StreamUrlResolver streamUrlResolver = new StreamUrlResolver();
    private int currentIndex = -1;
    private String currentTitle = "Voice Chat Audio";
    private String currentArtist = "Voice Chat";
    private String currentSourceUrl;
    // Track currently-loading index to avoid duplicate resolves
    private volatile int resolvingIndex = -1;
    // Client-provided duration hint (e.g. from MediaStore for saved tracks) — used when
    // ExoPlayer hasn't parsed metadata yet so the progress bar is usable from the start.
    private long hintDurationMs = 0;
    private final Handler progressHandler = new Handler(Looper.getMainLooper());
    private final Runnable progressTicker = new Runnable() {
        @Override
        public void run() {
            if (player == null) return;
            int state = player.getPlaybackState();
            // Always re-emit status while player is alive (not IDLE/ENDED).
            // Don't gate on isPlaying() — audio focus dips can flip it false transiently.
            if (state == Player.STATE_READY || state == Player.STATE_BUFFERING) {
                broadcastStatus(null);
                progressHandler.postDelayed(this, 1000);
            }
        }
    };

    @Override
    public void onCreate() {
        super.onCreate();
        createNotificationChannel();

        // Use extended HTTP timeout: HLS proxy's first request calls yt-dlp (30-40s)
        DefaultHttpDataSource.Factory httpDataSourceFactory = new DefaultHttpDataSource.Factory()
            .setConnectTimeoutMs(60_000)
            .setReadTimeoutMs(60_000);
        // DefaultDataSource.Factory routes content:// to ContentDataSource, file:// to FileDataSource,
        // http(s):// to our tuned HttpDataSource. Required so locally-saved tracks play.
        DefaultDataSource.Factory dataSourceFactory = new DefaultDataSource.Factory(this, httpDataSourceFactory);
        player = new ExoPlayer.Builder(this)
            .setMediaSourceFactory(new DefaultMediaSourceFactory(dataSourceFactory))
            .build();
        player.setWakeMode(C.WAKE_MODE_NETWORK);
        player.setAudioAttributes(
            new AudioAttributes.Builder()
                .setUsage(C.USAGE_MEDIA)
                .setContentType(C.AUDIO_CONTENT_TYPE_MUSIC)
                .build(),
            true
        );
        // MediaSession: tells the OS this is a media player → proper wake lock, lock screen controls
        mediaSession = new MediaSession.Builder(this, player).build();

        player.addListener(new Player.Listener() {
            @Override
            public void onPlaybackStateChanged(int state) {
                Log.d(TAG, "onPlaybackStateChanged state=" + playbackStateName(state));
                updateNotification();
                broadcastStatus(null);
                // Auto-advance to next track when current track ends
                if (state == Player.STATE_ENDED) {
                    if (currentIndex >= 0 && currentIndex < rawPlaylist.size() - 1) {
                        Log.d(TAG, "Track ended → auto next track " + (currentIndex + 1));
                        currentIndex++;
                        playCurrent();
                    } else {
                        Log.d(TAG, "Playlist ended");
                    }
                }
            }

            @Override
            public void onIsPlayingChanged(boolean isPlaying) {
                Log.d(TAG, "onIsPlayingChanged isPlaying=" + isPlaying);
                updateNotification();
                broadcastStatus(null);
                progressHandler.removeCallbacks(progressTicker);
                // Run ticker whenever the player is alive (READY/BUFFERING),
                // not only when isPlaying — keeps UI consistent across audio-focus blips.
                int s = player != null ? player.getPlaybackState() : Player.STATE_IDLE;
                if (s == Player.STATE_READY || s == Player.STATE_BUFFERING) {
                    progressHandler.post(progressTicker);
                }
            }

            @Override
            public void onPositionDiscontinuity(Player.PositionInfo oldPosition, Player.PositionInfo newPosition, int reason) {
                broadcastStatus(null);
            }

            @Override
            public void onPlayerError(PlaybackException error) {
                Log.e(TAG, "onPlayerError code=" + error.errorCode + " msg=" + error.getMessage(), error);
                // BehindLiveWindowException: player fell behind the live edge.
                // Seek to default (live edge) and re-prepare instead of erroring out.
                if (error.errorCode == PlaybackException.ERROR_CODE_BEHIND_LIVE_WINDOW) {
                    Log.i(TAG, "Behind live window — seeking to live edge and re-preparing");
                    player.seekToDefaultPosition();
                    player.prepare();
                    return;
                }
                broadcastStatus(error.getMessage());
            }
        });
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        if (intent == null || intent.getAction() == null) {
            Log.w(TAG, "onStartCommand called with null intent/action");
            return START_STICKY;
        }

        String action = intent.getAction();
        Log.d(TAG, "onStartCommand action=" + action + " startId=" + startId);
        // Ping action: immediately broadcast current status so JS can pick up state on resume
        if ("com.tyranokim.voicechat.audio.ACTION_PING".equals(action)) {
            broadcastStatus(null);
            return START_STICKY;
        }
        switch (action) {
            case BackgroundAudioPlugin.ACTION_PLAY:
                handlePlay(intent);
                break;
            case BackgroundAudioPlugin.ACTION_PAUSE:
                // Serialize on player's looper so consecutive pause/resume don't race
                if (player != null) {
                    final Player p = player;
                    progressHandler.post(() -> p.setPlayWhenReady(false));
                }
                break;
            case BackgroundAudioPlugin.ACTION_RESUME:
                if (player != null) {
                    final Player p = player;
                    progressHandler.post(() -> {
                        try {
                            int s = p.getPlaybackState();
                            Log.i(TAG, "Resume from " + playbackStateName(s) + " mediaItems=" + p.getMediaItemCount());
                            if (s == Player.STATE_IDLE || s == Player.STATE_ENDED || p.getMediaItemCount() == 0) {
                                stopped = false;
                                playCurrent();
                            } else {
                                p.setPlayWhenReady(true);
                            }
                        } catch (Exception ex) {
                            Log.e(TAG, "RESUME failed: " + ex.getMessage(), ex);
                        }
                    });
                }
                break;
            case BackgroundAudioPlugin.ACTION_STOP:
                stopPlayback();
                break;
            case BackgroundAudioPlugin.ACTION_NEXT:
                playNext();
                break;
            case BackgroundAudioPlugin.ACTION_PREV:
                playPrev();
                break;
            case BackgroundAudioPlugin.ACTION_SEEK:
                int positionMs = intent.getIntExtra(BackgroundAudioPlugin.EXTRA_POSITION_MS, -1);
                if (player != null && positionMs >= 0) {
                    player.seekTo(positionMs);
                }
                break;
            case BackgroundAudioPlugin.ACTION_RATE:
                float rate = intent.getFloatExtra(BackgroundAudioPlugin.EXTRA_RATE, 1.0f);
                if (player != null) {
                    player.setPlaybackParameters(new PlaybackParameters(rate));
                    Log.i(TAG, "Playback rate set to " + rate);
                }
                break;
            default:
                break;
        }

        updateNotification();
        broadcastStatus(null);
        return START_STICKY;
    }

    private void handlePlay(Intent intent) {
        String url = intent.getStringExtra(BackgroundAudioPlugin.EXTRA_URL);
        if (url == null || url.isEmpty()) {
            Log.e(TAG, "handlePlay missing playable URL");
            broadcastStatus("Missing URL");
            return;
        }

        currentSourceUrl = intent.getStringExtra(BackgroundAudioPlugin.EXTRA_SOURCE_URL);
        String sourceType = valueOrDefault(intent.getStringExtra(BackgroundAudioPlugin.EXTRA_URL_TYPE), streamUrlResolver.classify(currentSourceUrl));
        Log.i(TAG, "handlePlay sourceType=" + sourceType + " source=" + currentSourceUrl);

        currentTitle = valueOrDefault(intent.getStringExtra(BackgroundAudioPlugin.EXTRA_TITLE), "Voice Chat Audio");
        currentArtist = valueOrDefault(intent.getStringExtra(BackgroundAudioPlugin.EXTRA_ARTIST), "Voice Chat");
        hintDurationMs = intent.getLongExtra(BackgroundAudioPlugin.EXTRA_DURATION_MS, 0);
        Log.i(TAG, "handlePlay hintFromIntent=" + hintDurationMs + " url=" + url);
        // For content:// URIs (local saved tracks), ALWAYS probe — never trust just the JS hint.
        // MediaStore DURATION is authoritative (we confirmed listTracks returns correct value),
        // so use max(hint, queried) to be defensive against silent JS/bridge serialization issues.
        if (url != null && url.startsWith("content://")) {
            android.net.Uri u = android.net.Uri.parse(url);
            long probed = 0;
            try { probed = queryContentDuration(u); } catch (Exception ignored) {}
            Log.i(TAG, "handlePlay queryContentDuration=" + probed);
            if (probed <= 0) {
                try { probed = mediaMetadataDuration(u); } catch (Exception ignored) {}
                Log.i(TAG, "handlePlay mediaMetadataDuration=" + probed);
            }
            if (probed <= 0) {
                try { probed = mediaPlayerDuration(u); } catch (Exception ignored) {}
                Log.i(TAG, "handlePlay mediaPlayerDuration=" + probed);
            }
            if (probed > hintDurationMs) hintDurationMs = probed;
        }
        stopped = false; // reset stop guard on new play
        Log.i(TAG, "handlePlay hintDuration=" + hintDurationMs + " url=" + url);

        // Prefer EXTRA_RAW_PLAYLIST (lazy resolve). Fall back to EXTRA_PLAYLIST (legacy: already-resolved).
        String rawJson = intent.getStringExtra(BackgroundAudioPlugin.EXTRA_RAW_PLAYLIST);
        boolean isResolved = false;
        if (rawJson == null || rawJson.isEmpty()) {
            rawJson = intent.getStringExtra(BackgroundAudioPlugin.EXTRA_PLAYLIST);
            isResolved = true; // legacy: items already playable
        }
        int requestedIndex = intent.getIntExtra(BackgroundAudioPlugin.EXTRA_INDEX, -1);

        rawPlaylist.clear();
        resolvedCache.clear();

        if (rawJson != null) {
            try {
                JSONArray arr = new JSONArray(rawJson);
                for (int i = 0; i < arr.length(); i++) {
                    String item = arr.optString(i, null);
                    if (item != null && !item.isEmpty()) {
                        rawPlaylist.add(item);
                        resolvedCache.add(isResolved ? item : null);
                    }
                }
            } catch (Exception e) {
                Log.w(TAG, "Failed to parse playlist JSON", e);
            }
        }

        if (rawPlaylist.isEmpty()) {
            rawPlaylist.add(valueOrDefault(currentSourceUrl, url));
            resolvedCache.add(url); // current is already resolved
            currentIndex = 0;
        } else {
            // Find requestedIndex; else find by sourceUrl; else 0
            currentIndex = (requestedIndex >= 0 && requestedIndex < rawPlaylist.size())
                ? requestedIndex
                : Math.max(0, currentSourceUrl != null ? rawPlaylist.indexOf(currentSourceUrl) : 0);
        }

        // Cache the already-resolved current URL so we don't re-resolve immediately
        if (currentIndex >= 0 && currentIndex < resolvedCache.size()) {
            resolvedCache.set(currentIndex, url);
        }

        playCurrent();
    }

    /**
     * Play the track at currentIndex. If its resolved URL isn't cached yet,
     * resolve it in the background and play once ready. Service main thread is
     * never blocked by network I/O.
     */
    private void playCurrent() {
        if (player == null || currentIndex < 0 || currentIndex >= rawPlaylist.size()) {
            Log.w(TAG, "playCurrent skipped (invalid state) index=" + currentIndex + " size=" + rawPlaylist.size());
            return;
        }

        String cached = currentIndex < resolvedCache.size() ? resolvedCache.get(currentIndex) : null;
        if (cached != null && !cached.isEmpty()) {
            playUrl(cached);
            // Pre-warm next item resolution in background to make track changes feel instant
            prefetchNext();
            return;
        }

        // Not yet resolved → broadcast buffering and resolve in background
        broadcastStatus(null);
        final int idx = currentIndex;
        if (resolvingIndex == idx) return; // already resolving
        resolvingIndex = idx;
        new Thread(() -> {
            try {
                String raw = rawPlaylist.get(idx);
                Log.i(TAG, "Resolving track " + idx + " lazily: " + raw);
                StreamUrlResolver.ResolveResult r = streamUrlResolver.resolve(raw, null);
                if (r.ok && r.playableUrl != null) {
                    if (idx < resolvedCache.size()) resolvedCache.set(idx, r.playableUrl);
                    // Only play if user hasn't already skipped to another track
                    if (!stopped && idx == currentIndex) {
                        progressHandler.post(() -> {
                            playUrl(r.playableUrl);
                            prefetchNext();
                        });
                    }
                } else {
                    Log.w(TAG, "Resolve failed for track " + idx + ": " + r.message);
                    progressHandler.post(() -> broadcastStatus("재생 불가: " + r.message));
                }
            } finally {
                resolvingIndex = -1;
            }
        }).start();
    }

    /** Resolve the next track in background to make ⏭ feel instant. */
    private void prefetchNext() {
        int nextIdx = currentIndex + 1;
        if (nextIdx >= rawPlaylist.size() || nextIdx >= resolvedCache.size()) return;
        if (resolvedCache.get(nextIdx) != null) return;
        new Thread(() -> {
            try {
                String raw = rawPlaylist.get(nextIdx);
                StreamUrlResolver.ResolveResult r = streamUrlResolver.resolve(raw, null);
                if (r.ok && r.playableUrl != null && nextIdx < resolvedCache.size()) {
                    resolvedCache.set(nextIdx, r.playableUrl);
                    Log.d(TAG, "Prefetched track " + nextIdx);
                }
            } catch (Exception e) {
                Log.w(TAG, "prefetchNext error: " + e.getMessage());
            }
        }).start();
    }

    private void playUrl(String currentUrl) {
        if (player == null || currentUrl == null) return;
        String urlType = streamUrlResolver.classify(currentUrl);
        Log.i(TAG, "playUrl index=" + currentIndex + " urlType=" + urlType + " url=" + currentUrl);

        boolean isLiveProxy = currentUrl.contains("/hls-proxy");
        MediaItem.Builder mediaItemBuilder = new MediaItem.Builder()
            .setUri(currentUrl)
            .setMimeType(inferMimeType(currentUrl));
        if (isLiveProxy) {
            // Live stream: stay 5s behind live edge for stability
            mediaItemBuilder.setLiveConfiguration(
                new MediaItem.LiveConfiguration.Builder()
                    .setTargetOffsetMs(5_000)
                    .setMinOffsetMs(0)
                    .setMaxOffsetMs(20_000)
                    .build()
            );
            Log.i(TAG, "Live stream configured with LiveConfiguration for " + currentUrl);
        }
        MediaItem mediaItem = mediaItemBuilder.build();

        player.setMediaItem(mediaItem);
        player.prepare();
        player.play();

        Notification notification = buildNotification();
        Log.i(TAG, "startForeground id=" + NOTIFICATION_ID + " title=" + currentTitle);
        // Android 14+ (UPSIDE_DOWN_CAKE, API 34) requires explicit foreground service type
        // matching one declared in the manifest, or startForeground throws SecurityException.
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.UPSIDE_DOWN_CAKE) {
            try {
                startForeground(NOTIFICATION_ID, notification, ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PLAYBACK);
            } catch (Exception e) {
                Log.e(TAG, "startForeground (typed) failed: " + e.getMessage(), e);
                broadcastStatus("foreground service: " + e.getMessage());
            }
        } else {
            startForeground(NOTIFICATION_ID, notification);
        }
    }

    private void playNext() {
        if (currentIndex < rawPlaylist.size() - 1) {
            currentIndex++;
            playCurrent();
        }
    }

    private void playPrev() {
        if (currentIndex > 0) {
            currentIndex--;
            playCurrent();
        } else if (player != null) {
            player.seekTo(0);
        }
    }

    private boolean stopped = false;
    private synchronized void stopPlayback() {
        // Idempotent stop. We do NOT call stopSelf — keeping the service alive avoids
        // the onCreate/onDestroy race where a quick second ⏹ tap crashes the new instance
        // (MediaSession collision or null player). Android will GC us when memory needs it.
        if (stopped && (player == null || player.getPlaybackState() == Player.STATE_IDLE)) {
            Log.d(TAG, "stopPlayback called again (already idle), ignoring");
            return;
        }
        try {
            if (player != null) {
                player.setPlayWhenReady(false);
                player.stop();
                player.clearMediaItems();
            }
        } catch (Exception e) {
            Log.w(TAG, "player.stop() failed: " + e.getMessage());
        }
        resolvingIndex = -1;
        stopped = true;
        progressHandler.removeCallbacks(progressTicker);
        try { stopForeground(STOP_FOREGROUND_REMOVE); } catch (Exception ignored) {}
        broadcastStatus(null);
    }

    private Notification buildNotification() {
        String title = currentTitle;
        String text = currentArtist;

        NotificationCompat.Builder builder = new NotificationCompat.Builder(this, CHANNEL_ID)
            .setSmallIcon(R.mipmap.ic_launcher)
            .setContentTitle(title)
            .setContentText(text)
            .setOngoing(player != null && player.isPlaying())
            .setOnlyAlertOnce(true)
            .setVisibility(NotificationCompat.VISIBILITY_PUBLIC);

        // MediaStyle: shows media controls on lock screen and keeps OS from killing us
        if (mediaSession != null) {
            builder.setStyle(new MediaStyleNotificationHelper.MediaStyle(mediaSession));
        }

        return builder.build();
    }

    private void updateNotification() {
        NotificationManager nm = getSystemService(NotificationManager.class);
        if (nm != null) {
            nm.notify(NOTIFICATION_ID, buildNotification());
        }
    }

    private void createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationChannel channel = new NotificationChannel(
                CHANNEL_ID,
                "Background Audio",
                NotificationManager.IMPORTANCE_LOW
            );
            channel.setDescription("Voice Chat background audio playback");
            NotificationManager nm = getSystemService(NotificationManager.class);
            if (nm != null) {
                nm.createNotificationChannel(channel);
            }
        }
    }

    private void broadcastStatus(@Nullable String error) {
        Intent status = new Intent(BackgroundAudioPlugin.ACTION_STATUS);
        boolean playing = player != null && player.isPlaying();
        int state = player != null ? player.getPlaybackState() : Player.STATE_IDLE;

        boolean resolving = resolvingIndex == currentIndex && currentIndex >= 0;
        boolean playWhenReady = player != null && player.getPlayWhenReady();
        long playerDur = player != null ? player.getDuration() : C.TIME_UNSET;
        long effectiveDur = (playerDur != C.TIME_UNSET && playerDur > 0) ? playerDur : hintDurationMs;
        long pos = player != null ? player.getCurrentPosition() : 0;
        if (pos < 0) pos = 0;
        status.putExtra("playing", playing);
        status.putExtra("playWhenReady", playWhenReady);
        status.putExtra("buffering", state == Player.STATE_BUFFERING || resolving);
        status.putExtra("positionMs", pos);
        status.putExtra("durationMs", Math.max(0, effectiveDur));
        status.putExtra("index", currentIndex);
        status.putExtra("hasNext", currentIndex >= 0 && currentIndex < rawPlaylist.size() - 1);
        status.putExtra("hasPrev", currentIndex > 0);
        String currentRaw = currentIndex >= 0 && currentIndex < rawPlaylist.size() ? rawPlaylist.get(currentIndex) : null;
        String currentResolved = currentIndex >= 0 && currentIndex < resolvedCache.size() ? resolvedCache.get(currentIndex) : null;
        status.putExtra("currentUrl", currentResolved != null ? currentResolved : currentRaw);
        status.putExtra("title", currentTitle);
        status.putExtra("artist", currentArtist);
        status.putExtra("playbackState", playbackStateName(state));
        // JS-friendly state string. Use playWhenReady (user intent) over isPlaying
        // so brief audio-focus dips don't flip UI to "paused" while user is listening.
        String stateStr;
        switch (state) {
            case Player.STATE_IDLE: stateStr = "idle"; break;
            case Player.STATE_BUFFERING: stateStr = playWhenReady ? "buffering" : "paused"; break;
            case Player.STATE_READY: stateStr = playWhenReady ? "playing" : "paused"; break;
            case Player.STATE_ENDED: stateStr = "ended"; break;
            default: stateStr = "idle";
        }
        status.putExtra("state", stateStr);
        if (error != null) {
            status.putExtra("error", error);
        }

        // Explicit package targeting: ensures broadcast is delivered to our app's receiver
        // even with Android 14+ stricter broadcast routing rules.
        status.setPackage(getPackageName());
        sendBroadcast(status);
    }

    private String inferMimeType(String url) {
        String lower = url != null ? url.toLowerCase() : "";
        if (lower.contains(".m3u8") || lower.contains("/hls-proxy")) return MimeTypes.APPLICATION_M3U8;
        if (lower.contains(".mpd")) return MimeTypes.APPLICATION_MPD;
        if (lower.contains(".mp3")) return MimeTypes.AUDIO_MPEG;
        if (lower.contains(".m4a")) return MimeTypes.AUDIO_MP4;
        if (lower.contains(".aac")) return MimeTypes.AUDIO_AAC;
        if (lower.contains(".ogg")) return MimeTypes.AUDIO_OGG;
        if (lower.contains(".wav")) return MimeTypes.AUDIO_WAV;
        if (lower.contains(".flac")) return MimeTypes.AUDIO_FLAC;
        return null;
    }

    private String valueOrDefault(String value, String fallback) {
        return value == null || value.isEmpty() ? fallback : value;
    }

    // Probe duration via MediaMetadataRetriever using a FileDescriptor (required for
    // content:// URIs under Scoped Storage — (Context, Uri) variant silently fails).
    private long mediaMetadataDuration(android.net.Uri uri) {
        android.os.ParcelFileDescriptor pfd = null;
        android.media.MediaMetadataRetriever mmr = null;
        try {
            pfd = getContentResolver().openFileDescriptor(uri, "r");
            if (pfd == null) return 0;
            mmr = new android.media.MediaMetadataRetriever();
            mmr.setDataSource(pfd.getFileDescriptor());
            String d = mmr.extractMetadata(android.media.MediaMetadataRetriever.METADATA_KEY_DURATION);
            if (d != null) {
                long ms = Long.parseLong(d);
                Log.i(TAG, "mediaMetadataDuration → " + ms + "ms");
                return ms;
            }
        } catch (Exception e) {
            Log.w(TAG, "mediaMetadataDuration failed: " + e.getClass().getSimpleName() + ": " + e.getMessage());
        } finally {
            if (mmr != null) try { mmr.release(); } catch (Exception ignored) {}
            if (pfd != null) try { pfd.close(); } catch (Exception ignored) {}
        }
        return 0;
    }

    private long mediaPlayerDuration(android.net.Uri uri) {
        android.os.ParcelFileDescriptor pfd = null;
        android.media.MediaPlayer mediaPlayer = null;
        try {
            pfd = getContentResolver().openFileDescriptor(uri, "r");
            if (pfd == null) return 0;
            mediaPlayer = new android.media.MediaPlayer();
            mediaPlayer.setDataSource(pfd.getFileDescriptor());
            mediaPlayer.prepare();
            long ms = mediaPlayer.getDuration();
            if (ms > 0) {
                Log.i(TAG, "mediaPlayerDuration -> " + ms + "ms");
                return ms;
            }
        } catch (Exception e) {
            Log.w(TAG, "mediaPlayerDuration failed: " + e.getClass().getSimpleName() + ": " + e.getMessage());
        } finally {
            if (mediaPlayer != null) try { mediaPlayer.release(); } catch (Exception ignored) {}
            if (pfd != null) try { pfd.close(); } catch (Exception ignored) {}
        }
        return 0;
    }

    private long queryContentDuration(android.net.Uri uri) {
        try (android.database.Cursor c = getContentResolver().query(
                uri,
                new String[]{android.provider.MediaStore.Audio.Media.DURATION},
                null, null, null)) {
            if (c != null && c.moveToFirst()) {
                int idx = c.getColumnIndex(android.provider.MediaStore.Audio.Media.DURATION);
                if (idx >= 0) return c.getLong(idx);
            }
        } catch (Exception e) {
            Log.w(TAG, "queryContentDuration failed: " + e.getMessage());
        }
        return 0;
    }

    private String playbackStateName(int state) {
        switch (state) {
            case Player.STATE_IDLE:
                return "IDLE";
            case Player.STATE_BUFFERING:
                return "BUFFERING";
            case Player.STATE_READY:
                return "READY";
            case Player.STATE_ENDED:
                return "ENDED";
            default:
                return "UNKNOWN(" + state + ")";
        }
    }

    @Override
    public void onDestroy() {
        progressHandler.removeCallbacks(progressTicker);
        if (mediaSession != null) {
            mediaSession.release();
            mediaSession = null;
        }
        if (player != null) {
            player.release();
            player = null;
        }
        super.onDestroy();
    }

    @Nullable
    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }
}
