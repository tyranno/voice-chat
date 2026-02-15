import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
	appId: 'com.tyranokim.voicechat',
	appName: 'VoiceChat',
	webDir: 'build',
	server: {
		androidScheme: 'https',
		cleartext: true
	},
	android: {
		allowMixedContent: true
	},
	plugins: {
		SplashScreen: {
			launchShowDuration: 2000,
			launchAutoHide: true,
			launchFadeOutDuration: 500,
			backgroundColor: '#030712',
			androidSplashResourceName: 'splash',
			androidScaleType: 'CENTER_CROP',
			showSpinner: false,
			splashFullScreen: true,
			splashImmersive: true
		}
	}
};

export default config;
