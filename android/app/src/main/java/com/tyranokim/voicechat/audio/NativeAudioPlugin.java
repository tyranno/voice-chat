package com.tyranokim.voicechat.audio;

import android.media.AudioAttributes;
import android.media.AudioManager;
import android.media.AudioFocusRequest;
import android.content.Context;
import android.speech.tts.TextToSpeech;
import android.speech.tts.UtteranceProgressListener;
import android.util.Log;

import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;

import java.util.Locale;
import java.util.HashMap;
import java.util.concurrent.atomic.AtomicInteger;

@CapacitorPlugin(name = "NativeAudio")
public class NativeAudioPlugin extends Plugin {
    private static final String TAG = "NativeAudio";
    private TextToSpeech tts;
    private boolean ttsReady = false;
    private float speechRate = 1.0f;
    private AtomicInteger utteranceId = new AtomicInteger(0);
    private PluginCall pendingCall;
    private AudioFocusRequest audioFocusRequest;

    @Override
    public void load() {
        super.load();
        tts = new TextToSpeech(getContext(), status -> {
            if (status == TextToSpeech.SUCCESS) {
                int result = tts.setLanguage(Locale.KOREAN);
                if (result == TextToSpeech.LANG_MISSING_DATA || result == TextToSpeech.LANG_NOT_SUPPORTED) {
                    Log.e(TAG, "Korean TTS not supported");
                } else {
                    ttsReady = true;
                    tts.setSpeechRate(speechRate);
                    // Use NAVIGATION_GUIDANCE usage - plays even in VIBRATE/DND mode
                    tts.setAudioAttributes(new AudioAttributes.Builder()
                        .setUsage(AudioAttributes.USAGE_ASSISTANCE_NAVIGATION_GUIDANCE)  // Navigation guidance bypasses VIBRATE mode
                        .setContentType(AudioAttributes.CONTENT_TYPE_SPEECH)
                        .setLegacyStreamType(AudioManager.STREAM_MUSIC)
                        .build());
                    Log.d(TAG, "TTS ready, engine: " + tts.getDefaultEngine());
                }
            } else {
                Log.e(TAG, "TTS init failed: " + status);
            }
        });
    }

    @PluginMethod
    public void speak(PluginCall call) {
        String text = call.getString("text", "");
        if (text.isEmpty()) {
            call.resolve();
            return;
        }
        if (!ttsReady) {
            Log.e(TAG, "TTS not ready");
            call.reject("TTS not ready");
            return;
        }

        try {
            ensureMediaVolume();

            // Request audio focus for navigation guidance
            final AudioManager am = (AudioManager) getContext().getSystemService(Context.AUDIO_SERVICE);
            audioFocusRequest = new AudioFocusRequest.Builder(AudioManager.AUDIOFOCUS_GAIN_TRANSIENT_MAY_DUCK)
                .setAudioAttributes(new AudioAttributes.Builder()
                    .setUsage(AudioAttributes.USAGE_ASSISTANCE_NAVIGATION_GUIDANCE)
                    .setContentType(AudioAttributes.CONTENT_TYPE_SPEECH)
                    .build())
                .build();
            am.requestAudioFocus(audioFocusRequest);

            String id = "utt_" + utteranceId.incrementAndGet();
            pendingCall = call;

        tts.setOnUtteranceProgressListener(new UtteranceProgressListener() {
            @Override
            public void onStart(String utteranceId) {
                Log.d(TAG, "Speaking: " + text.substring(0, Math.min(text.length(), 30)));
            }
            @Override
            public void onDone(String utteranceId) {
                Log.d(TAG, "Speech done");
                // Abandon audio focus when done
                if (audioFocusRequest != null) {
                    am.abandonAudioFocusRequest(audioFocusRequest);
                    audioFocusRequest = null;
                }
                notifyListeners("audioEnded", new JSObject());
                if (pendingCall != null) {
                    pendingCall.resolve();
                    pendingCall = null;
                }
            }
            @Override
            public void onError(String utteranceId) {
                Log.e(TAG, "Speech error");
                // Abandon audio focus on error
                if (audioFocusRequest != null) {
                    am.abandonAudioFocusRequest(audioFocusRequest);
                    audioFocusRequest = null;
                }
                if (pendingCall != null) {
                    pendingCall.reject("Speech error");
                    pendingCall = null;
                }
            }
        });

            tts.speak(text, TextToSpeech.QUEUE_FLUSH, null, id);
        } catch (Exception e) {
            Log.e(TAG, "Speak failed", e);
            // Abandon audio focus on exception
            if (audioFocusRequest != null) {
                AudioManager am = (AudioManager) getContext().getSystemService(Context.AUDIO_SERVICE);
                am.abandonAudioFocusRequest(audioFocusRequest);
                audioFocusRequest = null;
            }
            if (pendingCall != null) {
                pendingCall.reject("Speech failed: " + e.getMessage());
                pendingCall = null;
            }
        }
    }

    @PluginMethod
    public void stop(PluginCall call) {
        if (tts != null) {
            tts.stop();
        }
        // Abandon audio focus if active
        if (audioFocusRequest != null) {
            AudioManager am = (AudioManager) getContext().getSystemService(Context.AUDIO_SERVICE);
            am.abandonAudioFocusRequest(audioFocusRequest);
            audioFocusRequest = null;
        }
        if (pendingCall != null) {
            pendingCall.resolve();
            pendingCall = null;
        }
        call.resolve();
    }

    @PluginMethod
    public void setRate(PluginCall call) {
        speechRate = call.getFloat("rate", 1.0f);
        if (tts != null && ttsReady) {
            tts.setSpeechRate(speechRate);
        }
        call.resolve();
    }

    // Keep these for backward compat but they just call speak
    @PluginMethod
    public void playBase64(PluginCall call) {
        call.resolve(); // no-op, deprecated
    }

    @PluginMethod
    public void playUrl(PluginCall call) {
        call.resolve(); // no-op, deprecated
    }

    private void ensureMediaVolume() {
        try {
            AudioManager am = (AudioManager) getContext().getSystemService(Context.AUDIO_SERVICE);
            int current = am.getStreamVolume(AudioManager.STREAM_MUSIC);
            int max = am.getStreamMaxVolume(AudioManager.STREAM_MUSIC);
            if (current == 0) {
                am.setStreamVolume(AudioManager.STREAM_MUSIC, (int)(max * 0.6), 0);
                Log.d(TAG, "Volume was 0, set to " + (int)(max * 0.6));
            }
        } catch (Exception e) {
            Log.w(TAG, "ensureMediaVolume: " + e.getMessage());
        }
    }

    @Override
    public void handleOnDestroy() {
        if (tts != null) {
            tts.stop();
            tts.shutdown();
        }
        super.handleOnDestroy();
    }
}
