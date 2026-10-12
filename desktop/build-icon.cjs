// Package the approved transparent VEYRA icon as a Windows PNG-backed ICO.
'use strict';
const fs=require('node:fs'),path=require('node:path');
const png=fs.readFileSync(path.join(__dirname,'assets','veyra-icon.png'));
if(png.readUInt32BE(16)!==256||png.readUInt32BE(20)!==256)throw Error('Icon must be 256 by 256 pixels.');
const ico=Buffer.alloc(22);ico.writeUInt16LE(1,2);ico.writeUInt16LE(1,4);ico.writeUInt16LE(1,10);ico.writeUInt16LE(32,12);ico.writeUInt32LE(png.length,14);ico.writeUInt32LE(22,18);
fs.mkdirSync(path.join(__dirname,'build'),{recursive:true});fs.writeFileSync(path.join(__dirname,'build','icon.ico'),Buffer.concat([ico,png]));
