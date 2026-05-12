package com.tyranokim.voicechat.audio;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.os.Build;
import android.util.Log;

import androidx.core.content.ContextCompat;

import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;

import org.json.JSONArray;

import java.util.ArrayList;
import java.util.List;

@CapacitorPlugin(name = "BackgroundAudio")
public class BackgroundAudioPlugin extends Plugin {
    private static final String TAG = "BgAudioPlugin";

    public static final String ACTION_PLAY = "com.tyranokim.voicechat.audio.ACTION_PLAY";
    public static final String ACTION_PAUSE = "com.tyranokim.voicechat.audio.ACTION_PAUSE";
    public static final String ACTION_RESUME = "com.tyranokim.voicechat.audio.ACTION_RESUME";
    public static final String ACTION_STOP = "com.tyranokim.voicechat.audio.ACTION_STOP";
    public static final String ACTION_NEXT = "com.tyranokim.voicechat.audio.ACTION_NEXT";
    public static final String ACTION_PREV = "com.tyranokim.voicechat.audio.ACTION_PREV";
    public static final String ACTION_SEEK = "com.tyranokim.voicechat.audio.ACTION_SEEK";
    public static final String ACTION_RATE = "com.tyranokim.voicechat.audio.ACTION_RATE";
    public static final String ACTION_STATUS = "com.tyranokim.voicechat.audio.ACTION_STATUS";

    public static final String EXTRA_URL = "url";
    public static final String EXTRA_TITLE = "title";
    public static final String EXTRA_ARTIST = "artist";
    public static final String EXTRA_PLAYLIST = "playlist";        // resolved URLs (legacy)
    public static final String EXTRA_RAW_PLAYLIST = "rawPlaylist"; // raw source URLs (new, lazy resolve)
    public static final String EXTRA_INDEX = "index";
    public static final String EXTRA_SOURCE_URL = "sourceUrl";
    public static final String EXTRA_URL_TYPE = "urlType";
    public static final String EXTRA_POSITION_MS = "positionMs";
    public static final String EXTRA_RATE = "rate";
    public static final String EXTRA_DURATION_MS = "durationMs";

    private BroadcastReceiver statusReceiver;
    private final StreamUrlResolver streamUrlResolver = new StreamUrlResolver();

    @Override
    public void load() {
        super.load();

        statusReceiver = new BroadcastReceiver() {
            @Override
            public void onReceive(Context context, Intent intent) {
                JSObject payload = new JSObject();
                payload.put("playing", intent.getBooleanExtra("playing", false));
                payload.put("playWhenReady", intent.getBooleanExtra("playWhenReady", false));
                payload.put("buffering", intent.getBooleanExtra("buffering", false));
                payload.put("currentUrl", intent.getStringExtra("currentUrl"));
                payload.put("title", intent.getStringExtra("title"));
                payload.put("artist", intent.getStringExtra("artist"));
                payload.put("positionMs", intent.getLongExtra("positionMs", 0));
                payload.put("durationMs", intent.getLongExtra("durationMs", 0));
                payload.put("index", intent.getIntExtra("index", -1));
                payload.put("hasNext", intent.getBooleanExtra("hasNext", false));
                payload.put("hasPrev", intent.getBooleanExtra("hasPrev", false));
                payload.put("error", intent.getStringExtra("error"));
                payload.put("state", intent.getStringExtra("state"));
                payload.put("playbackState", intent.getStringExtra("playbackState"));
                notifyListeners("status", payload, true);
            }
        };

        IntentFilter filter = new IntentFilter(ACTION_STATUS);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            getContext().registerReceiver(statusReceiver, filter, Context.RECEIVER_NOT_EXPORTED);
        } else {
            getContext().registerReceiver(statusReceiver, filter);
        }
    }

    @Override
    protected void handleOnDestroy() {
        super.handleOnDestroy();
        try {
            if (statusReceiver != null) {
                getContext().unregisterReceiver(statusReceiver);
                statusReceiver = null;
            }
        } catch (Exception ignored) {
        }
    }

    @PluginMethod
    public void play(PluginCall call) {
        String sourceUrl = call.getString("url");
        if (sourceUrl == null || sourceUrl.isEmpty()) {
            call.reject("url is required");
            return;
        }

        new Thread(() -> {
            try {
                String playableHint = call.getString("resolvedUrl", call.getString("playableUrl", null));
                // Resolve ONLY the currently-requested track so playback starts quickly.
                // Remaining playlist items resolve lazily in the service on track change.
                StreamUrlResolver.ResolveResult current = streamUrlResolver.resolve(sourceUrl, playableHint);
                if (!current.ok || current.playableUrl == null) {
                    String error = current.message != null ? current.message : "Failed to resolve playable URL";
                    Log.e(TAG, "play rejected: sourceType=" + current.sourceType + " reason=" + error);
                    getActivity().runOnUiThread(() -> call.reject(error));
                    return;
                }

                List<String> rawPlaylist = collectRawPlaylist(call.getArray("playlist"), sourceUrl);
                int requestedIndex = call.getInt("index", -1);

                Intent intent = serviceIntent(ACTION_PLAY);
                intent.putExtra(EXTRA_URL, current.playableUrl);
                intent.putExtra(EXTRA_SOURCE_URL, sourceUrl);
                intent.putExtra(EXTRA_URL_TYPE, current.sourceType);
                intent.putExtra(EXTRA_TITLE, call.getString("title", "Voice Chat Audio"));
                intent.putExtra(EXTRA_ARTIST, call.getString("artist", "Voice Chat"));
                intent.putExtra(EXTRA_RAW_PLAYLIST, new JSONArray(rawPlaylist).toString());
                intent.putExtra(EXTRA_INDEX, requestedIndex);
                // Use raw JSON access so larger values + double-encoded numbers don't lose precision
                long durHintLong = 0L;
                try {
                    Object durRaw = call.getData().opt("durationMs");
                    if (durRaw instanceof Number) {
                        durHintLong = ((Number) durRaw).longValue();
                    }
                } catch (Exception ignored) {}
                if (durHintLong > 0) {
                    intent.putExtra(EXTRA_DURATION_MS, durHintLong);
                }
                final long durHint = durHintLong;

                Log.i(TAG, "play -> service: sourceType=" + current.sourceType + ", rawPlaylistSize=" + rawPlaylist.size() + " durationHintMs=" + durHint + " (lazy resolve enabled)");
                startService(intent);
                getActivity().runOnUiThread(call::resolve);
            } catch (Exception e) {
                Log.e(TAG, "play failed", e);
                String msg = e.getMessage() != null ? e.getMessage() : "play failed";
                getActivity().runOnUiThread(() -> call.reject(msg));
            }
        }).start();
    }

    @PluginMethod
    public void pause(PluginCall call) {
        startService(serviceIntent(ACTION_PAUSE));
        call.resolve();
    }

    @PluginMethod
    public void resume(PluginCall call) {
        startService(serviceIntent(ACTION_RESUME));
        call.resolve();
    }

    @PluginMethod
    public void stop(PluginCall call) {
        startService(serviceIntent(ACTION_STOP));
        call.resolve();
    }

    @PluginMethod
    public void next(PluginCall call) {
        startService(serviceIntent(ACTION_NEXT));
        call.resolve();
    }

    @PluginMethod
    public void prev(PluginCall call) {
        startService(serviceIntent(ACTION_PREV));
        call.resolve();
    }

    @PluginMethod
    public void getStatus(PluginCall call) {
        // Force a status broadcast so JS can fill state on app resume / first mount
        Intent intent = serviceIntent("com.tyranokim.voicechat.audio.ACTION_PING");
        startService(intent);
        // Build a quick best-effort snapshot from the service's last-known fields via broadcast
        // The actual status arrives via the broadcast receiver shortly after.
        JSObject result = new JSObject();
        result.put("requested", true);
        call.resolve(result);
    }

    @PluginMethod
    public void setRate(PluginCall call) {
        Double rateD = call.getDouble("rate", 1.0);
        float rate = rateD != null ? rateD.floatValue() : 1.0f;
        if (rate < 0.25f) rate = 0.25f;
        if (rate > 3.0f) rate = 3.0f;
        Intent intent = serviceIntent(ACTION_RATE);
        intent.putExtra(EXTRA_RATE, rate);
        startService(intent);
        call.resolve();
    }

    @PluginMethod
    public void seek(PluginCall call) {
        int positionMs = call.getInt("positionMs", -1);
        if (positionMs < 0) {
            call.reject("positionMs is required");
            return;
        }
        Intent intent = serviceIntent(ACTION_SEEK);
        intent.putExtra(EXTRA_POSITION_MS, positionMs);
        startService(intent);
        call.resolve();
    }

    /**
     * Collect raw playlist URLs WITHOUT resolving them. The service will resolve
     * each item lazily when it's about to play (on track end / next / prev).
     * This keeps the play() promise fast (one resolve, not N).
     */
    private List<String> collectRawPlaylist(JSONArray playlistArray, String fallbackSourceUrl) {
        List<String> raw = new ArrayList<>();
        if (playlistArray != null && playlistArray.length() > 0) {
            for (int i = 0; i < playlistArray.length(); i++) {
                String item = playlistArray.optString(i, null);
                if (item != null && !item.isEmpty()) {
                    raw.add(item);
                }
            }
        }
        if (raw.isEmpty() && fallbackSourceUrl != null && !fallbackSourceUrl.isEmpty()) {
            raw.add(fallbackSourceUrl);
        }
        return raw;
    }

    private Intent serviceIntent(String action) {
        Intent intent = new Intent(getContext(), BackgroundAudioService.class);
        intent.setAction(action);
        return intent;
    }

    private void startService(Intent intent) {
        // Only ACTION_PLAY actually starts a foreground media session (playUrl calls
        // startForeground). Other actions (PING/PAUSE/STOP/SEEK/RATE/NEXT/PREV/RESUME) only
        // fire while the WebView/Activity is visible — plain startService is sufficient and
        // safe. Using startForegroundService for these would trip the
        // ForegroundServiceDidNotStartInTimeException timer (~5s) and randomly kill the app.
        String action = intent.getAction();
        if (ACTION_PLAY.equals(action)) {
            ContextCompat.startForegroundService(getContext(), intent);
        } else {
            try {
                getContext().startService(intent);
            } catch (IllegalStateException e) {
                Log.w(TAG, "startService(" + action + ") failed: " + e.getMessage());
            }
        }
    }
}
