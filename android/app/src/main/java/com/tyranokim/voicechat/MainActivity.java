package com.tyranokim.voicechat;

import android.os.Bundle;
import com.getcapacitor.BridgeActivity;
import com.tyranokim.voicechat.stt.NativeSttPlugin;

public class MainActivity extends BridgeActivity {
    @Override
    public void onCreate(Bundle savedInstanceState) {
        registerPlugin(NativeSttPlugin.class);
        super.onCreate(savedInstanceState);
    }
}
