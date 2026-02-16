package com.tyranokim.voicechat;

import android.os.Bundle;
import com.getcapacitor.BridgeActivity;
import com.tyranokim.voicechat.stt.NativeSttPlugin;
import com.tyranokim.voicechat.updater.AppUpdaterPlugin;
import com.tyranokim.voicechat.downloader.FileDownloaderPlugin;
import com.tyranokim.voicechat.audio.NativeAudioPlugin;
import com.tyranokim.voicechat.fcm.FcmPlugin;

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
        registerPlugin(FcmPlugin.class);
        super.onCreate(savedInstanceState);
    }
}
