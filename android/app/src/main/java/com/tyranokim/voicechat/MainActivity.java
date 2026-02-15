package com.tyranokim.voicechat;

import android.os.Bundle;
import com.getcapacitor.BridgeActivity;
import com.tyranokim.voicechat.stt.NativeSttPlugin;
import com.tyranokim.voicechat.updater.AppUpdaterPlugin;
import com.tyranokim.voicechat.downloader.FileDownloaderPlugin;

public class MainActivity extends BridgeActivity {
    @Override
    public void onCreate(Bundle savedInstanceState) {
        registerPlugin(NativeSttPlugin.class);
        registerPlugin(AppUpdaterPlugin.class);
        registerPlugin(FileDownloaderPlugin.class);
        super.onCreate(savedInstanceState);
    }
}
