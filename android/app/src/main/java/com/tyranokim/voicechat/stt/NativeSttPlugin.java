package com.tyranokim.voicechat.stt;

import android.Manifest;
import android.content.Context;
import android.content.Intent;
import android.media.AudioManager;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.speech.RecognitionListener;
import android.speech.RecognizerIntent;
import android.speech.SpeechRecognizer;
import android.util.Log;

import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;
import com.getcapacitor.annotation.Permission;

import java.util.ArrayList;

@CapacitorPlugin(
    name = "NativeStt",
    permissions = {
        @Permission(strings = { Manifest.permission.RECORD_AUDIO }, alias = "microphone")
    }
)
public class NativeSttPlugin extends Plugin {
    private static final String TAG = "NativeStt";
    private static final long RESTART_DELAY_MS = 150;
    private static final long MIN_SPEECH_DURATION_MS = 600; // 이보다 짧으면 노이즈로 간주, 조용히 재시작

    private SpeechRecognizer recognizer;
    private volatile boolean isListening = false;
    private volatile boolean shouldRestart = false;
    private final Handler handler = new Handler(Looper.getMainLooper());
    private String lastFinalText = "";
    private long lastFinalTime = 0;
    private int consecutiveErrors = 0;

    // 음성 시작 시각 추적
    private long speechStartTime = 0;
    private boolean speechDetected = false;

    // RMS 추적
    private float maxRms = 0;
    private int rmsLogCounter = 0;

    // 시스템 사운드 뮤트
    private int savedNotificationVolume = -1;
    private int savedSystemVolume = -1;
    private int savedRingVolume = -1;

    @PluginMethod
    public void start(PluginCall call) {
        if (isListening) {
            call.resolve();
            return;
        }

        if (!hasPermission(Manifest.permission.RECORD_AUDIO)) {
            requestAllPermissions(call, "micPermCallback");
            return;
        }

        shouldRestart = true;
        consecutiveErrors = 0;
        startListening(call);
    }

    @PluginMethod
    public void stop(PluginCall call) {
        Log.d(TAG, "stop() called");
        shouldRestart = false;
        handler.removeCallbacksAndMessages(null);
        unmuteSystemSoundsInternal();
        destroyRecognizer();
        call.resolve();
    }

    @PluginMethod
    public void pause(PluginCall call) {
        Log.d(TAG, "pause()");
        shouldRestart = false;
        handler.removeCallbacksAndMessages(null);
        unmuteSystemSoundsInternal();
        // pause: stopListening만 (destroy하지 않음)
        isListening = false;
        getActivity().runOnUiThread(() -> {
            if (recognizer != null) {
                try { recognizer.stopListening(); } catch (Exception ignored) {}
            }
        });
        call.resolve();
    }

    @PluginMethod
    public void resume(PluginCall call) {
        Log.d(TAG, "resume()");
        shouldRestart = true;
        consecutiveErrors = 0;
        restartListening(call);
    }

    @PluginMethod
    public void isListening(PluginCall call) {
        JSObject result = new JSObject();
        result.put("listening", isListening);
        call.resolve(result);
    }

    @PluginMethod
    public void muteSystemSounds(PluginCall call) {
        muteSystemSoundsInternal();
        call.resolve();
    }

    @PluginMethod
    public void unmuteSystemSounds(PluginCall call) {
        unmuteSystemSoundsInternal();
        call.resolve();
    }

    // ── Internal mute/unmute ──

    private void muteSystemSoundsInternal() {
        try {
            AudioManager am = (AudioManager) getContext().getSystemService(Context.AUDIO_SERVICE);
            if (savedNotificationVolume < 0) {
                savedNotificationVolume = am.getStreamVolume(AudioManager.STREAM_NOTIFICATION);
                savedSystemVolume = am.getStreamVolume(AudioManager.STREAM_SYSTEM);
                savedRingVolume = am.getStreamVolume(AudioManager.STREAM_RING);
            }
            am.setStreamVolume(AudioManager.STREAM_NOTIFICATION, 0, 0);
            am.setStreamVolume(AudioManager.STREAM_SYSTEM, 0, 0);
            am.setStreamVolume(AudioManager.STREAM_RING, 0, 0);
        } catch (Exception e) {
            Log.w(TAG, "mute error: " + e.getMessage());
        }
    }

    private void unmuteSystemSoundsInternal() {
        try {
            AudioManager am = (AudioManager) getContext().getSystemService(Context.AUDIO_SERVICE);
            if (savedNotificationVolume >= 0) {
                am.setStreamVolume(AudioManager.STREAM_NOTIFICATION, savedNotificationVolume, 0);
                am.setStreamVolume(AudioManager.STREAM_SYSTEM, savedSystemVolume, 0);
                am.setStreamVolume(AudioManager.STREAM_RING, savedRingVolume, 0);
                savedNotificationVolume = -1;
                savedSystemVolume = -1;
                savedRingVolume = -1;
            }
        } catch (Exception e) {
            Log.w(TAG, "unmute error: " + e.getMessage());
        }
    }

    // ── Permission callback ──

    @com.getcapacitor.annotation.PermissionCallback
    private void micPermCallback(PluginCall call) {
        if (hasPermission(Manifest.permission.RECORD_AUDIO)) {
            shouldRestart = true;
            startListening(call);
        } else {
            call.reject("마이크 권한이 필요합니다");
        }
    }

    // ── Recognizer management ──

    private Intent createRecognizerIntent() {
        Intent intent = new Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH);
        intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM);
        intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE, "ko-KR");
        intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE_PREFERENCE, "ko-KR");
        intent.putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true);
        intent.putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 1);
        intent.putExtra(RecognizerIntent.EXTRA_CALLING_PACKAGE, getContext().getPackageName());
        // 침묵 타임아웃 — 좀 더 여유있게
        intent.putExtra(RecognizerIntent.EXTRA_SPEECH_INPUT_COMPLETE_SILENCE_LENGTH_MILLIS, 2000L);
        intent.putExtra(RecognizerIntent.EXTRA_SPEECH_INPUT_POSSIBLY_COMPLETE_SILENCE_LENGTH_MILLIS, 2000L);
        intent.putExtra(RecognizerIntent.EXTRA_SPEECH_INPUT_MINIMUM_LENGTH_MILLIS, 1000L);
        return intent;
    }

    private final RecognitionListener recognitionListener = new RecognitionListener() {
        @Override
        public void onReadyForSpeech(Bundle params) {
            Log.d(TAG, "Ready for speech");
            isListening = true;
            consecutiveErrors = 0;
            speechDetected = false;
            maxRms = 0;
        }

        @Override
        public void onBeginningOfSpeech() {
            speechStartTime = System.currentTimeMillis();
            speechDetected = true;
            Log.d(TAG, "Speech started");
        }

        @Override
        public void onRmsChanged(float rmsdB) {
            if (rmsdB > maxRms) maxRms = rmsdB;
            // 매 50번째만 로그 (노이즈 줄이기)
            if (++rmsLogCounter % 50 == 0) {
                Log.d(TAG, "RMS: " + String.format("%.1f", rmsdB) + " (max: " + String.format("%.1f", maxRms) + ")");
            }
        }

        @Override public void onBufferReceived(byte[] buffer) {}

        @Override
        public void onEndOfSpeech() {
            long duration = speechDetected ? (System.currentTimeMillis() - speechStartTime) : 0;
            Log.d(TAG, "Speech ended (duration=" + duration + "ms, maxRms=" + String.format("%.1f", maxRms) + ")");
        }

        @Override
        public void onError(int error) {
            String msg = getErrorText(error);
            long duration = speechDetected ? (System.currentTimeMillis() - speechStartTime) : 0;
            boolean isNoise = (error == SpeechRecognizer.ERROR_NO_MATCH && duration < MIN_SPEECH_DURATION_MS);
            isListening = false;

            if (isNoise) {
                // 짧은 노이즈 — 조용히 빠르게 재시작 (로그도 최소화)
                if (consecutiveErrors % 20 == 0) {
                    Log.d(TAG, "Noise skip x" + (consecutiveErrors + 1) + " (duration=" + duration + "ms)");
                }
                consecutiveErrors++;
                if (shouldRestart) {
                    scheduleRestart(100); // 노이즈는 100ms로 빠르게
                }
                return;
            }

            Log.w(TAG, "Error: " + msg + " (code=" + error + ", duration=" + duration + "ms, maxRms=" + String.format("%.1f", maxRms) + ")");
            consecutiveErrors++;

            // 에러 이벤트 → JS (연속 10회 이상만)
            if (consecutiveErrors >= 10) {
                JSObject event = new JSObject();
                event.put("type", "error");
                event.put("text", msg + " (연속 " + consecutiveErrors + "회)");
                notifyListeners("sttResult", event);
            }

            // 자동 재시작 — recognizer 재사용
            if (shouldRestart && (error == SpeechRecognizer.ERROR_NO_MATCH
                    || error == SpeechRecognizer.ERROR_SPEECH_TIMEOUT
                    || error == SpeechRecognizer.ERROR_CLIENT)) {
                long delay = consecutiveErrors > 10 ? 3000 : RESTART_DELAY_MS;
                scheduleRestart(delay);
            } else if (shouldRestart && error == SpeechRecognizer.ERROR_RECOGNIZER_BUSY) {
                scheduleRestart(1000);
            }
        }

        @Override
        public void onResults(Bundle results) {
            ArrayList<String> matches = results.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION);
            if (matches != null && !matches.isEmpty()) {
                String text = matches.get(0);
                long now = System.currentTimeMillis();
                if (!text.equals(lastFinalText) || (now - lastFinalTime) > 500) {
                    Log.d(TAG, "Final: " + text);
                    JSObject event = new JSObject();
                    event.put("type", "final");
                    event.put("text", text);
                    notifyListeners("sttResult", event);
                    lastFinalText = text;
                    lastFinalTime = now;
                    consecutiveErrors = 0;
                } else {
                    Log.d(TAG, "Duplicate final ignored: " + text);
                }
            }

            isListening = false;
            if (shouldRestart) {
                scheduleRestart(RESTART_DELAY_MS);
            }
        }

        @Override
        public void onPartialResults(Bundle partialResults) {
            ArrayList<String> matches = partialResults.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION);
            if (matches != null && !matches.isEmpty()) {
                String text = matches.get(0);
                if (!text.isEmpty()) {
                    JSObject event = new JSObject();
                    event.put("type", "partial");
                    event.put("text", text);
                    notifyListeners("sttResult", event);
                }
            }
        }

        @Override public void onEvent(int eventType, Bundle params) {}
    };

    /**
     * 첫 시작: recognizer 생성 + startListening
     */
    private void startListening(PluginCall call) {
        getActivity().runOnUiThread(() -> {
            try {
                // 기존 인스턴스가 있으면 재사용
                if (recognizer == null) {
                    Log.d(TAG, "Creating new SpeechRecognizer");
                    recognizer = SpeechRecognizer.createSpeechRecognizer(getContext());
                    recognizer.setRecognitionListener(recognitionListener);
                }

                rmsLogCounter = 0;
                recognizer.startListening(createRecognizerIntent());
                Log.d(TAG, "Listening started");
                if (call != null) call.resolve();
            } catch (Exception e) {
                Log.e(TAG, "Start error: " + e.getMessage());
                // 에러 시 recognizer 재생성 시도
                destroyRecognizerOnUiThread();
                if (call != null) call.reject("시작 실패: " + e.getMessage());
            }
        });
    }

    /**
     * 재시작: recognizer 재사용하여 startListening만 호출
     */
    private void restartListening(PluginCall call) {
        getActivity().runOnUiThread(() -> {
            try {
                if (recognizer == null) {
                    Log.d(TAG, "Recreating SpeechRecognizer for restart");
                    recognizer = SpeechRecognizer.createSpeechRecognizer(getContext());
                    recognizer.setRecognitionListener(recognitionListener);
                } else {
                    // cancel() 호출로 이전 세션 확실히 종료 (BUSY 방지)
                    try { recognizer.cancel(); } catch (Exception ignored) {}
                }

                rmsLogCounter = 0;
                recognizer.startListening(createRecognizerIntent());
                Log.d(TAG, "Restart listening");
                if (call != null) call.resolve();
            } catch (Exception e) {
                Log.e(TAG, "Restart error: " + e.getMessage() + " — recreating recognizer");
                // 실패하면 destroy 후 재생성
                destroyRecognizerOnUiThread();
                try {
                    recognizer = SpeechRecognizer.createSpeechRecognizer(getContext());
                    recognizer.setRecognitionListener(recognitionListener);
                    recognizer.startListening(createRecognizerIntent());
                    if (call != null) call.resolve();
                } catch (Exception e2) {
                    Log.e(TAG, "Restart failed completely: " + e2.getMessage());
                    if (call != null) call.reject("재시작 실패: " + e2.getMessage());
                }
            }
        });
    }

    private void scheduleRestart(long delay) {
        if (!shouldRestart) return;
        Log.d(TAG, "Scheduling restart in " + delay + "ms (errors=" + consecutiveErrors + ")");
        handler.postDelayed(() -> {
            if (shouldRestart) {
                restartListening(null);
            }
        }, delay);
    }

    private void destroyRecognizerOnUiThread() {
        if (recognizer != null) {
            try { recognizer.stopListening(); } catch (Exception ignored) {}
            try { recognizer.destroy(); } catch (Exception ignored) {}
            recognizer = null;
        }
    }

    private void destroyRecognizer() {
        isListening = false;
        getActivity().runOnUiThread(this::destroyRecognizerOnUiThread);
        Log.d(TAG, "Recognizer destroyed");
    }

    private String getErrorText(int errorCode) {
        switch (errorCode) {
            case SpeechRecognizer.ERROR_AUDIO: return "AUDIO";
            case SpeechRecognizer.ERROR_CLIENT: return "CLIENT";
            case SpeechRecognizer.ERROR_INSUFFICIENT_PERMISSIONS: return "NO_PERMISSION";
            case SpeechRecognizer.ERROR_NETWORK: return "NETWORK";
            case SpeechRecognizer.ERROR_NETWORK_TIMEOUT: return "NETWORK_TIMEOUT";
            case SpeechRecognizer.ERROR_NO_MATCH: return "NO_MATCH";
            case SpeechRecognizer.ERROR_RECOGNIZER_BUSY: return "BUSY";
            case SpeechRecognizer.ERROR_SERVER: return "SERVER";
            case SpeechRecognizer.ERROR_SPEECH_TIMEOUT: return "SPEECH_TIMEOUT";
            default: return "UNKNOWN(" + errorCode + ")";
        }
    }
}
