package com.tyranokim.voicechat;

import android.os.Bundle;
import android.util.Log;

import androidx.activity.OnBackPressedCallback;

import com.getcapacitor.BridgeActivity;
import com.tyranokim.voicechat.stt.NativeSttPlugin;
import com.tyranokim.voicechat.updater.AppUpdaterPlugin;
import com.tyranokim.voicechat.downloader.FileDownloaderPlugin;
import com.tyranokim.voicechat.audio.NativeAudioPlugin;
// import com.tyranokim.voicechat.fcm.FcmPlugin;  // google-services.json 없으면 크래시

public class MainActivity extends BridgeActivity {
    private static MainActivity instance;

    public static MainActivity getInstance() {
        return instance;
    }

    @Override
    public void onCreate(Bundle savedInstanceState) {
        instance = this;
        registerPlugin(NativeSttPlugin.class);
        registerPlugin(AppUpdaterPlugin.class);
        registerPlugin(FileDownloaderPlugin.class);
        registerPlugin(NativeAudioPlugin.class);
        // registerPlugin(FcmPlugin.class);  // FCM 비활성화 (google-services.json 필요)
        super.onCreate(savedInstanceState);

        // 뒤로가기 버튼 → WebView JS 이벤트로 전달 (앱 종료 방지)
        getOnBackPressedDispatcher().addCallback(this, new OnBackPressedCallback(true) {
            @Override
            public void handleOnBackPressed() {
                Log.d("MainActivity", "Back button pressed → forwarding to WebView");
                if (getBridge() != null && getBridge().getWebView() != null) {
                    getBridge().getWebView().evaluateJavascript(
                        "window.dispatchEvent(new CustomEvent('hardwareBackPress'));", null);
                }
            }
        });
    }
}
