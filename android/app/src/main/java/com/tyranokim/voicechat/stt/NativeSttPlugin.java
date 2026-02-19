package com.tyranokim.voicechat.stt;

import android.Manifest;
import android.media.AudioFormat;
import android.media.AudioRecord;
import android.media.MediaRecorder;
import android.util.Log;

import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;
import com.getcapacitor.annotation.Permission;

import org.json.JSONObject;

import java.nio.ByteBuffer;
import java.nio.ByteOrder;

import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.Response;
import okhttp3.WebSocket;
import okhttp3.WebSocketListener;
import okio.ByteString;

@CapacitorPlugin(
    name = "NativeStt",
    permissions = {
        @Permission(strings = { Manifest.permission.RECORD_AUDIO }, alias = "microphone")
    }
)
public class NativeSttPlugin extends Plugin {
    private static final String TAG = "NativeStt";
    private static final int SAMPLE_RATE = 16000;

    private static NativeSttPlugin instance;

    private AudioRecord audioRecord;
    private Thread recordingThread;
    private OkHttpClient httpClient;
    private WebSocket webSocket;

    private volatile boolean isRunning = false;
    private volatile boolean isPaused = false;
    private volatile boolean wasConnected = false;  // 한번이라도 연결 성공했는지
    private volatile int reconnectCount = 0;
    private String serverUrl = "";

    // 중복 결과 방지
    private String lastFinalText = "";
    private long lastFinalTime = 0;

    public static NativeSttPlugin getInstance() {
        return instance;
    }

    @Override
    public void load() {
        super.load();
        instance = this;
        httpClient = new OkHttpClient.Builder()
            .retryOnConnectionFailure(true)
            .build();
    }

    public boolean isCurrentlyListening() {
        return isRunning && !isPaused;
    }

    public void resumeFromLifecycle() {
        Log.d(TAG, "resumeFromLifecycle()");
    }

    @PluginMethod
    public void start(PluginCall call) {
        if (isRunning) {
            call.resolve();
            return;
        }

        if (!hasPermission(Manifest.permission.RECORD_AUDIO)) {
            requestAllPermissions(call, "micPermCallback");
            return;
        }

        // Get server URL from JS
        String url = call.getString("serverUrl", "");
        if (url != null && !url.isEmpty()) {
            serverUrl = url;
        }

        if (serverUrl.isEmpty()) {
            call.reject("서버 URL이 설정되지 않았습니다");
            return;
        }

        startRecording();
        call.resolve();
    }

    @PluginMethod
    public void stop(PluginCall call) {
        Log.d(TAG, "stop()");
        stopRecording();
        call.resolve();
    }

    public void forceStop() {
        Log.d(TAG, "forceStop()");
        stopRecording();
    }

    @PluginMethod
    public void pause(PluginCall call) {
        Log.d(TAG, "pause() — TTS 재생 중 에코 방지");
        isPaused = true;
        // 서버에 일시정지 알림 (서버가 잔여 오디오 처리하지 않도록)
        if (webSocket != null) {
            try { webSocket.send("{\"pause\":true}"); } catch (Exception ignored) {}
        }
        call.resolve();
    }

    @PluginMethod
    public void resume(PluginCall call) {
        Log.d(TAG, "resume() — STT 재개");
        isPaused = false;
        if (webSocket != null) {
            try { webSocket.send("{\"resume\":true}"); } catch (Exception ignored) {}
        } else if (isRunning) {
            // WebSocket died during pause — reconnect
            Log.d(TAG, "WebSocket dead after pause, reconnecting");
            if (getActivity() != null) {
                getActivity().runOnUiThread(() -> reconnect());
            }
        }
        call.resolve();
    }

    @PluginMethod
    public void isListening(PluginCall call) {
        JSObject result = new JSObject();
        result.put("listening", isRunning && !isPaused);
        call.resolve(result);
    }

    @PluginMethod
    public void muteSystemSounds(PluginCall call) { call.resolve(); }

    @PluginMethod
    public void unmuteSystemSounds(PluginCall call) { call.resolve(); }

    @com.getcapacitor.annotation.PermissionCallback
    private void micPermCallback(PluginCall call) {
        if (hasPermission(Manifest.permission.RECORD_AUDIO)) {
            String url = call.getString("serverUrl", "");
            if (url != null && !url.isEmpty()) serverUrl = url;
            startRecording();
            call.resolve();
        } else {
            call.reject("마이크 권한이 필요합니다");
        }
    }

    private void startRecording() {
        if (isRunning) return;

        // Build WebSocket URL: https → wss, http → ws
        String wsUrl = serverUrl
            .replace("https://", "wss://")
            .replace("http://", "ws://");
        if (!wsUrl.endsWith("/")) wsUrl += "/";
        wsUrl += "api/stt/stream";

        Log.d(TAG, "Connecting to STT server: " + wsUrl);

        int bufferSize = Math.max(
            AudioRecord.getMinBufferSize(SAMPLE_RATE, AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT),
            4096
        );

        try {
            audioRecord = new AudioRecord(
                MediaRecorder.AudioSource.VOICE_RECOGNITION,
                SAMPLE_RATE,
                AudioFormat.CHANNEL_IN_MONO,
                AudioFormat.ENCODING_PCM_16BIT,
                bufferSize
            );
        } catch (SecurityException e) {
            Log.e(TAG, "AudioRecord permission denied");
            emitError("마이크 권한 거부");
            return;
        }

        if (audioRecord.getState() != AudioRecord.STATE_INITIALIZED) {
            Log.e(TAG, "AudioRecord init failed");
            emitError("마이크 초기화 실패");
            return;
        }

        isRunning = true;
        isPaused = false;

        // Connect WebSocket
        Request request = new Request.Builder().url(wsUrl).build();
        final int finalBufferSize = bufferSize;

        webSocket = httpClient.newWebSocket(request, new WebSocketListener() {
            @Override
            public void onOpen(WebSocket ws, Response response) {
                Log.d(TAG, "WebSocket connected");
                wasConnected = true;
                reconnectCount = 0;
                // Start recording after WebSocket is open
                if (audioRecord == null) {
                    Log.e(TAG, "audioRecord is null on WebSocket open, aborting");
                    ws.close(1000, "No audio recorder");
                    return;
                }
                audioRecord.startRecording();
                Log.d(TAG, "Recording started (Server STT, " + SAMPLE_RATE + "Hz)");

                recordingThread = new Thread(() -> {
                    byte[] buffer = new byte[finalBufferSize];
                    while (isRunning) {
                        if (audioRecord == null) {
                            Log.w(TAG, "audioRecord is null, exiting recording thread");
                            break;
                        }
                        int read;
                        try {
                            read = audioRecord.read(buffer, 0, buffer.length);
                        } catch (Exception e) {
                            Log.e(TAG, "audioRecord.read error: " + e.getMessage());
                            break;
                        }
                        if (read <= 0) continue;
                        if (isPaused) continue;

                        // Send PCM audio to server
                        try {
                            ws.send(ByteString.of(buffer, 0, read));
                        } catch (Exception e) {
                            Log.e(TAG, "WebSocket send error: " + e.getMessage());
                            break;
                        }
                    }
                }, "SttRecordingThread");
                recordingThread.start();
            }

            @Override
            public void onMessage(WebSocket ws, String text) {
                try {
                    JSONObject json = new JSONObject(text);
                    String type = json.optString("type", "");
                    String resultText = json.optString("text", "");

                    if (resultText.isEmpty()) return;
                    if (isPaused) return;

                    if ("final".equals(type)) {
                        long now = System.currentTimeMillis();
                        if (!resultText.equals(lastFinalText) || (now - lastFinalTime) > 500) {
                            Log.d(TAG, "Final: " + resultText);
                            JSObject event = new JSObject();
                            event.put("type", "final");
                            event.put("text", resultText);
                            notifyListeners("sttResult", event);
                            lastFinalText = resultText;
                            lastFinalTime = now;
                        }
                    } else if ("partial".equals(type)) {
                        JSObject event = new JSObject();
                        event.put("type", "partial");
                        event.put("text", resultText);
                        notifyListeners("sttResult", event);
                    }
                } catch (Exception e) {
                    Log.e(TAG, "Parse error: " + e.getMessage());
                }
            }

            @Override
            public void onFailure(WebSocket ws, Throwable t, Response response) {
                Log.e(TAG, "WebSocket failed: " + t.getMessage());
                reconnectCount++;
                // 첫 연결 자체가 실패한 경우에만 에러 표시
                if (!wasConnected && reconnectCount >= 3) {
                    emitError("STT 서버 연결 실패: " + t.getMessage());
                } else {
                    Log.d(TAG, "STT reconnecting silently... (attempt " + reconnectCount + ")");
                }
                // Auto-reconnect after delay (exponential backoff, max 10s)
                if (isRunning) {
                    long delay = Math.min(1000L * reconnectCount, 10000L);
                    try { Thread.sleep(delay); } catch (InterruptedException ignored) {}
                    if (isRunning) {
                        Log.d(TAG, "Reconnecting...");
                        if (getActivity() != null) {
                            getActivity().runOnUiThread(() -> reconnect());
                        }
                    }
                }
            }

            @Override
            public void onClosed(WebSocket ws, int code, String reason) {
                Log.d(TAG, "WebSocket closed: " + code + " " + reason);
                if (isRunning && getActivity() != null) {
                    getActivity().runOnUiThread(() -> reconnect());
                }
            }
        });
    }

    private void reconnect() {
        if (!isRunning) return;
        // Close old WebSocket
        if (webSocket != null) {
            try { webSocket.cancel(); } catch (Exception ignored) {}
            webSocket = null;
        }
        // Stop old AudioRecord
        if (audioRecord != null) {
            try { audioRecord.stop(); audioRecord.release(); } catch (Exception ignored) {}
            audioRecord = null;
        }
        if (recordingThread != null) {
            try { recordingThread.join(1000); } catch (InterruptedException ignored) {}
            recordingThread = null;
        }
        // Restart
        isRunning = false;
        startRecording();
    }

    private void stopRecording() {
        isRunning = false;
        isPaused = false;
        wasConnected = false;
        reconnectCount = 0;

        if (webSocket != null) {
            try {
                webSocket.send("{\"eof\":1}");
                webSocket.close(1000, "stopped");
            } catch (Exception ignored) {}
            webSocket = null;
        }

        if (recordingThread != null) {
            try { recordingThread.join(2000); } catch (InterruptedException ignored) {}
            recordingThread = null;
        }

        if (audioRecord != null) {
            try { audioRecord.stop(); audioRecord.release(); } catch (Exception ignored) {}
            audioRecord = null;
        }

        Log.d(TAG, "Recording stopped");
    }

    private void emitError(String msg) {
        getActivity().runOnUiThread(() -> {
            JSObject event = new JSObject();
            event.put("type", "error");
            event.put("text", msg);
            notifyListeners("sttResult", event);
        });
    }
}
