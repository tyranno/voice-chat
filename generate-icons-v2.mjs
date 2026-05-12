import sharp from 'sharp';
import { readFileSync, mkdirSync } from 'fs';
import { join } from 'path';

const BASE = process.cwd();
const RES = join(BASE, 'android/app/src/main/res');
const iconSvg = readFileSync(join(BASE, 'resources/icon.svg'));

const sizes = [
	['mipmap-mdpi', 48],
	['mipmap-hdpi', 72],
	['mipmap-xhdpi', 96],
	['mipmap-xxhdpi', 144],
	['mipmap-xxxhdpi', 192],
];

await sharp(iconSvg).resize(1024, 1024).png().toFile(join(BASE, 'resources/icon.png'));
console.log('icon.png 1024 OK');

for (const [folder, size] of sizes) {
	const dir = join(RES, folder);
	mkdirSync(dir, { recursive: true });
	await sharp(iconSvg).resize(size, size).png().toFile(join(dir, 'ic_launcher.png'));
	await sharp(iconSvg).resize(size, size).png().toFile(join(dir, 'ic_launcher_round.png'));
	await sharp(iconSvg).resize(size, size).png().toFile(join(dir, 'ic_launcher_foreground.png'));
	console.log(folder + ' ' + size);
}
console.log('Done');
