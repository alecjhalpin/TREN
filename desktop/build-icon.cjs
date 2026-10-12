// Small original abstract orb. Generate build resources without an asset dependency.
'use strict';
const fs=require('node:fs'),zlib=require('node:zlib');
function crc(bytes){let crc=0xffffffff;for(const byte of bytes){crc^=byte;for(let bit=0;bit<8;bit++)crc=(crc>>>1)^((crc&1)?0xedb88320:0)}return (crc^0xffffffff)>>>0}
function chunk(type,data){const name=Buffer.from(type),size=Buffer.alloc(4),check=Buffer.alloc(4);size.writeUInt32BE(data.length);check.writeUInt32BE(crc(Buffer.concat([name,data])));return Buffer.concat([size,name,data,check])}
const size=256,raw=Buffer.alloc((size*4+1)*size);
for(let y=0;y<size;y++)for(let x=0;x<size;x++){const d=Math.hypot(x-127.5,y-127.5),i=y*(size*4+1)+1+x*4;if(d<112){const glow=Math.max(0,1-Math.hypot(x-93,y-80)/220);raw[i]=Math.round(112+72*glow);raw[i+1]=Math.round(193+47*glow);raw[i+2]=Math.round(161+48*glow);raw[i+3]=255;if(d<43){raw[i]=24;raw[i+1]=25;raw[i+2]=27}}}
const header=Buffer.alloc(13);header.writeUInt32BE(size);header.writeUInt32BE(size,4);header[8]=8;header[9]=6;
const png=Buffer.concat([Buffer.from([137,80,78,71,13,10,26,10]),chunk('IHDR',header),chunk('IDAT',zlib.deflateSync(raw)),chunk('IEND',Buffer.alloc(0))]);
const ico=Buffer.alloc(22);ico.writeUInt16LE(1,2);ico.writeUInt16LE(1,4);ico.writeUInt16LE(1,10);ico.writeUInt16LE(32,12);ico.writeUInt32LE(png.length,14);ico.writeUInt32LE(22,18);
fs.mkdirSync(__dirname+'/build',{recursive:true});fs.writeFileSync(__dirname+'/build/icon.ico',Buffer.concat([ico,png]));
