const { deflateSync } = require('zlib');
const { writeFileSync } = require('fs');

const WIDTH = 480, HEIGHT = 800;
const signature = Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]);

function crc32(buf) {
  let crc = 0xFFFFFFFF;
  const table = new Int32Array(256);
  for (let i = 0; i < 256; i++) {
    let c = i;
    for (let j = 0; j < 8; j++) c = (c & 1) ? (0xEDB88320 ^ (c >>> 1)) : (c >>> 1);
    table[i] = c;
  }
  for (let i = 0; i < buf.length; i++) crc = table[(crc ^ buf[i]) & 0xFF] ^ (crc >>> 8);
  return (crc ^ 0xFFFFFFFF) >>> 0;
}

function chunk(type, data) {
  const len = Buffer.alloc(4); len.writeUInt32BE(data.length);
  const typeData = Buffer.concat([Buffer.from(type), data]);
  const crc = Buffer.alloc(4); crc.writeUInt32BE(crc32(typeData));
  return Buffer.concat([len, typeData, crc]);
}

const ihdr = Buffer.alloc(13);
ihdr.writeUInt32BE(WIDTH, 0); ihdr.writeUInt32BE(HEIGHT, 4);
ihdr[8] = 8; ihdr[9] = 2; // 8-bit RGB

const bgR = 3, bgG = 7, bgB = 18; // #030712
const dinoR = 59, dinoG = 130, dinoB = 246; // blue-500

const raw = Buffer.alloc(HEIGHT * (1 + WIDTH * 3));
for (let y = 0; y < HEIGHT; y++) {
  const off = y * (1 + WIDTH * 3);
  raw[off] = 0;
  for (let x = 0; x < WIDTH; x++) {
    const px = off + 1 + x * 3;
    raw[px] = bgR; raw[px+1] = bgG; raw[px+2] = bgB;
  }
}

// T-Rex pixel art
const dino = [
  [0,-12],[1,-12],[2,-12],[3,-12],
  [-1,-11],[0,-11],[1,-11],[2,-11],[3,-11],[4,-11],
  [-1,-10],[0,-10],[1,-10],[2,-10],[3,-10],[4,-10],
  [-1,-9],[0,-9],[1,-9],[4,-9],
  [-1,-8],[0,-8],[1,-8],[2,-8],[3,-8],[4,-8],
  [-1,-7],[0,-7],[4,-7],
  [-1,-6],[0,-6],[1,-6],[-1,-5],[0,-5],[1,-5],
  [-4,-4],[-3,-4],[-2,-4],[-1,-4],[0,-4],[1,-4],[2,-4],[3,-4],
  [-5,-3],[-4,-3],[-3,-3],[-2,-3],[-1,-3],[0,-3],[1,-3],[2,-3],[3,-3],[4,-3],
  [-5,-2],[-4,-2],[-3,-2],[-2,-2],[-1,-2],[0,-2],[1,-2],[2,-2],[3,-2],[4,-2],
  [-5,-1],[-4,-1],[-3,-1],[-2,-1],[-1,-1],[0,-1],[1,-1],[2,-1],[3,-1],[4,-1],
  [-5,0],[-4,0],[-3,0],[-2,0],[-1,0],[0,0],[1,0],[2,0],[3,0],
  [-4,1],[-3,1],[-2,1],[-1,1],[0,1],[1,1],[2,1],[3,1],
  [-3,2],[-2,2],[-1,2],[0,2],[1,2],[2,2],
  [-6,-2],[-7,-1],[-8,0],[5,-2],[6,-1],[7,0],
  [-3,3],[-2,3],[1,3],[2,3],[-3,4],[-2,4],[1,4],[2,4],
  [-3,5],[-2,5],[1,5],[2,5],[-4,6],[-3,6],[-2,6],[1,6],[2,6],[3,6],
  [-6,-3],[-7,-2],[-8,-1],[-9,0],[-10,1],[-11,2],
];

const cx = Math.floor(WIDTH/2), cy = Math.floor(HEIGHT/2) - 20, scale = 8;
for (const [dx,dy] of dino) {
  for (let sy=0; sy<scale; sy++) for (let sx=0; sx<scale; sx++) {
    const px = cx+dx*scale+sx, py = cy+dy*scale+sy;
    if (px>=0 && px<WIDTH && py>=0 && py<HEIGHT) {
      const off = py*(1+WIDTH*3)+1+px*3;
      raw[off]=dinoR; raw[off+1]=dinoG; raw[off+2]=dinoB;
    }
  }
}

const compressed = deflateSync(raw);
const png = Buffer.concat([signature, chunk('IHDR',ihdr), chunk('IDAT',compressed), chunk('IEND',Buffer.alloc(0))]);
writeFileSync('E:\\Project\\My\\voice-chat\\android\\app\\src\\main\\res\\drawable\\splash.png', png);
console.log('Splash generated:', png.length, 'bytes');
