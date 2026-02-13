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
	}
};

export default config;
