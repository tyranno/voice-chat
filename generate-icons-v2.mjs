import sharp from 'sharp';
import { readFileSync, mkdirSync } from 'fs';
import { join } from 'path';

const BASE = process.cwd();
const RES = join(BASE, 'android/app/src/main/res');
const iconSvg = readFileSync(join(BASE, 'resources/icon.svg'));
const fgSvg = readFileSync(join(BASE, 'resources/icon-foreground.svg'));
const splashSvg = readFileSync(join(BASE, 'resources/splash.svg'));

const iconSizes = [
	['mipmap-mdpi', 48],
	['mipmap-hdpi', 72],
	['mipmap-xhdpi', 96],
	['mipmap-xxhdpi', 144],
	['mipmap-xxxhdpi', 192],
];

// Capacitor splash sizes (port + land, all densities)
// land = landscape, port = portrait
const splashSizes = [
	['drawable-land-mdpi', 480, 320],
	['drawable-land-hdpi', 800, 480],
	['drawable-land-xhdpi', 1280, 720],
	['drawable-land-xxhdpi', 1600, 960],
	['drawable-land-xxxhdpi', 1920, 1280],
	['drawable-port-mdpi', 320, 480],
	['drawable-port-hdpi', 480, 800],
	['drawable-port-xhdpi', 720, 1280],
	['drawable-port-xxhdpi', 960, 1600],
	['drawable-port-xxxhdpi', 1280, 1920],
];

// === Master icon ===
await sharp(iconSvg).resize(1024, 1024).png().toFile(join(BASE, 'resources/icon.png'));
console.log('icon.png 1024 OK');

// === Per-density app icons ===
for (const [folder, size] of iconSizes) {
	const dir = join(RES, folder);
	mkdirSync(dir, { recursive: true });
	await sharp(iconSvg).resize(size, size).png().toFile(join(dir, 'ic_launcher.png'));
	await sharp(iconSvg).resize(size, size).png().toFile(join(dir, 'ic_launcher_round.png'));
	await sharp(fgSvg).resize(size, size).png().toFile(join(dir, 'ic_launcher_foreground.png'));
	console.log('icon ' + folder + ' ' + size);
}

// === Master splash ===
await sharp(splashSvg).resize(2732, 2732).png().toFile(join(BASE, 'resources/splash.png'));
console.log('splash.png 2732 OK');

// === Per-density splash (Capacitor expects splash.png in drawable-{port,land}-{density}) ===
for (const [folder, w, h] of splashSizes) {
	const dir = join(RES, folder);
	mkdirSync(dir, { recursive: true });
	// Center-cover the square splash SVG into the target landscape/portrait canvas.
	await sharp(splashSvg)
		.resize(w, h, { fit: 'cover', position: 'centre' })
		.png()
		.toFile(join(dir, 'splash.png'));
	console.log('splash ' + folder + ' ' + w + 'x' + h);
}

// === Also write a base drawable/splash.png for Capacitor fallback ===
mkdirSync(join(RES, 'drawable'), { recursive: true });
await sharp(splashSvg).resize(1920, 1920, { fit: 'cover' }).png()
	.toFile(join(RES, 'drawable/splash.png'));
console.log('splash drawable/ base OK');

console.log('Done');
