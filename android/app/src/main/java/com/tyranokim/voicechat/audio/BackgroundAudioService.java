package com.tyranokim.voicechat.audio;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.Service;
import android.content.Intent;
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
import androidx.media3.common.Player;
import androidx.media3.common.util.UnstableApi;
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
    private final List<String> playlist = new ArrayList<>();
    private final StreamUrlResolver streamUrlResolver = new StreamUrlResolver();
    private int currentIndex = -1;
    private String currentTitle = "Voice Chat Audio";
    private String currentArtist = "Voice Chat";
    private String currentSourceUrl;
    private final Handler progressHandler = new Handler(Looper.getMainLooper());
    private final Runnable progressTicker = new Runnable() {
        @Override
        public void run() {
            if (player != null && player.isPlaying()) {
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
        player = new ExoPlayer.Builder(this)
            .setMediaSourceFactory(new DefaultMediaSourceFactory(httpDataSourceFactory))
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
                    if (currentIndex >= 0 && currentIndex < playlist.size() - 1) {
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
                if (isPlaying) {
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
        switch (action) {
            case BackgroundAudioPlugin.ACTION_PLAY:
                handlePlay(intent);
                break;
            case BackgroundAudioPlugin.ACTION_PAUSE:
                if (player != null) {
                    player.pause();
                }
                break;
            case BackgroundAudioPlugin.ACTION_RESUME:
                if (player != null) {
                    player.play();
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

        String playlistJson = intent.getStringExtra(BackgroundAudioPlugin.EXTRA_PLAYLIST);
        int requestedIndex = intent.getIntExtra(BackgroundAudioPlugin.EXTRA_INDEX, -1);

        playlist.clear();

        if (playlistJson != null) {
            try {
                JSONArray arr = new JSONArray(playlistJson);
                for (int i = 0; i < arr.length(); i++) {
                    String item = arr.optString(i, null);
                    if (item != null && !item.isEmpty()) {
                        playlist.add(item);
                    }
                }
            } catch (Exception e) {
                Log.w(TAG, "Failed to parse playlist JSON", e);
            }
        }

        if (playlist.isEmpty()) {
            playlist.add(url);
            currentIndex = 0;
        } else {
            currentIndex = requestedIndex >= 0 && requestedIndex < playlist.size() ? requestedIndex : Math.max(0, playlist.indexOf(url));
            if (currentIndex < 0) {
                playlist.add(0, url);
                currentIndex = 0;
            }
        }

        playCurrent();
    }

    private void playCurrent() {
        if (player == null || currentIndex < 0 || currentIndex >= playlist.size()) {
            Log.w(TAG, "playCurrent skipped (invalid state) index=" + currentIndex + " size=" + playlist.size());
            return;
        }

        String currentUrl = playlist.get(currentIndex);
        String urlType = streamUrlResolver.classify(currentUrl);
        Log.i(TAG, "playCurrent index=" + currentIndex + " urlType=" + urlType + " url=" + currentUrl);

        boolean isLiveProxy = currentUrl != null && currentUrl.contains("/hls-proxy");
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
        startForeground(NOTIFICATION_ID, notification);
    }

    private void playNext() {
        if (currentIndex < playlist.size() - 1) {
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

    private void stopPlayback() {
        if (player != null) {
            player.stop();
            player.clearMediaItems();
        }
        progressHandler.removeCallbacks(progressTicker);
        stopForeground(STOP_FOREGROUND_REMOVE);
        stopSelf();
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

        status.putExtra("playing", playing);
        status.putExtra("buffering", state == Player.STATE_BUFFERING);
        status.putExtra("positionMs", player != null ? player.getCurrentPosition() : 0);
        status.putExtra("durationMs", player != null ? Math.max(0, player.getDuration()) : 0);
        status.putExtra("index", currentIndex);
        status.putExtra("hasNext", currentIndex >= 0 && currentIndex < playlist.size() - 1);
        status.putExtra("hasPrev", currentIndex > 0);
        status.putExtra("currentUrl", currentIndex >= 0 && currentIndex < playlist.size() ? playlist.get(currentIndex) : null);
        status.putExtra("title", currentTitle);
        status.putExtra("artist", currentArtist);
        status.putExtra("playbackState", playbackStateName(state));
        // JS-friendly state string
        String stateStr;
        switch (state) {
            case Player.STATE_IDLE: stateStr = "idle"; break;
            case Player.STATE_BUFFERING: stateStr = "buffering"; break;
            case Player.STATE_READY: stateStr = playing ? "playing" : "paused"; break;
            case Player.STATE_ENDED: stateStr = "ended"; break;
            default: stateStr = "idle";
        }
        status.putExtra("state", stateStr);
        if (error != null) {
            status.putExtra("error", error);
        }

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
