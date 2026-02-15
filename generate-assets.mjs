import sharp from 'sharp';
import { readFileSync, mkdirSync } from 'fs';
import { join } from 'path';

const BASE = 'E:/Project/My/voice-chat';
const RES = join(BASE, 'android/app/src/main/res');

const iconSvg = readFileSync(join(BASE, 'resources/icon.svg'));
const splashSvg = readFileSync(join(BASE, 'resources/splash.svg'));

// Icon sizes
const sizes = [
  ['mipmap-mdpi', 48],
  ['mipmap-hdpi', 72],
  ['mipmap-xhdpi', 96],
  ['mipmap-xxhdpi', 144],
  ['mipmap-xxxhdpi', 192],
];

async function generateIcons() {
  // Generate 1024x1024 source icon
  await sharp(iconSvg).resize(1024, 1024).png().toFile(join(BASE, 'resources/icon.png'));
  console.log('Generated resources/icon.png (1024x1024)');

  for (const [folder, size] of sizes) {
    const dir = join(RES, folder);
    mkdirSync(dir, { recursive: true });

    // Square icon
    await sharp(iconSvg).resize(size, size).png().toFile(join(dir, 'ic_launcher.png'));

    // Round icon (same image, Android handles masking via adaptive icon XML)
    await sharp(iconSvg).resize(size, size).png().toFile(join(dir, 'ic_launcher_round.png'));

    // Foreground for adaptive icons (with padding)
    const fgSize = Math.round(size * 1.5); // 108dp / 72dp ratio
    const padded = Math.round((fgSize - size * 0.7) / 2);
    const innerSize = Math.round(size * 0.7);

    // Create foreground: dino on transparent bg, centered with safe zone padding
    const fgSvg = Buffer.from(`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 108 108">
      <g transform="translate(54, 56) scale(0.045)" fill="white">
        <ellipse cx="0" cy="40" rx="140" ry="170"/>
        <path d="M-100,120 Q-200,100 -280,180 Q-300,200 -280,190 Q-180,130 -90,140Z"/>
        <path d="M60,-80 Q80,-160 60,-220 Q40,-260 80,-260 Q140,-240 120,-160 Q110,-100 90,-60Z"/>
        <ellipse cx="100" cy="-260" rx="90" ry="60"/>
        <path d="M120,-230 Q180,-230 200,-240 Q210,-250 200,-260 Q180,-255 120,-250Z"/>
        <circle cx="130" cy="-275" r="14" fill="#2563eb"/>
        <path d="M90,-20 Q130,-40 140,-20 Q135,-10 120,-10 Q100,0 90,-10Z"/>
        <path d="M-40,180 Q-50,260 -60,320 Q-70,340 -40,340 Q-20,340 -10,320 Q0,300 -10,260 Q-20,200 -20,180Z"/>
        <path d="M60,180 Q50,260 40,320 Q30,340 60,340 Q80,340 90,320 Q100,300 90,260 Q80,200 80,180Z"/>
        <path d="M-60,-60 L-80,-100 L-50,-70 L-70,-110 L-40,-80 L-55,-120 L-20,-80" opacity="0.8"/>
      </g>
    </svg>`);

    await sharp(fgSvg).resize(size, size).png().toFile(join(dir, 'ic_launcher_foreground.png'));

    console.log(`Generated ${folder}/ (${size}x${size})`);
  }
}

async function generateSplash() {
  const drawableDir = join(RES, 'drawable');
  mkdirSync(drawableDir, { recursive: true });

  // Splash at 2732x2732 source
  await sharp(splashSvg).resize(2732, 2732).png().toFile(join(BASE, 'resources/splash.png'));
  console.log('Generated resources/splash.png (2732x2732)');

  // Android splash drawable (smaller for actual use)
  await sharp(splashSvg).resize(640, 640).png().toFile(join(drawableDir, 'splash.png'));
  console.log('Generated drawable/splash.png (640x640)');

  // Also generate various drawable densities for splash
  const splashSizes = [
    ['drawable-mdpi', 480],
    ['drawable-hdpi', 800],
    ['drawable-xhdpi', 1280],
    ['drawable-xxhdpi', 1600],
    ['drawable-xxxhdpi', 1920],
  ];
  for (const [folder, size] of splashSizes) {
    const dir = join(RES, folder);
    mkdirSync(dir, { recursive: true });
    await sharp(splashSvg).resize(size, size).png().toFile(join(dir, 'splash.png'));
    console.log(`Generated ${folder}/splash.png (${size}x${size})`);
  }
}

await generateIcons();
await generateSplash();
console.log('\nDone! All assets generated.');
