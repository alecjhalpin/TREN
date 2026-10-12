'use strict';
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),http=require('node:http');
function installId(root){return crypto.createHash('sha256').update(process.platform==='win32'?path.resolve(root).toLowerCase():path.resolve(root)).digest('hex')}
function validRoot(root){try{return ['app.py','index.html','version.json'].every(f=>fs.statSync(path.join(root||'',f)).isFile())}catch{return false}}
function ready(root,body){if(body?.application!=='TREN'||body.installation!==installId(root)||!/^\d+\.\d+\.\d+$/.test(body.version||''))return false;const [major,minor]=body.version.split('.').map(Number);return major>0||minor>=10}
function request(port,method='GET',endpoint='/api/desktop/status',token='',payload={confirmed:true},withHeaders=false){
 return new Promise((resolve,reject)=>{const body=method==='POST'?JSON.stringify(payload):null;const req=http.request({host:'127.0.0.1',port,path:endpoint,method,timeout:3000,headers:body?{'Content-Type':'application/json','Content-Length':Buffer.byteLength(body),'X-TREN-Desktop':token}:{}},r=>{let raw='';r.on('data',c=>{raw+=c;if(raw.length>65536)req.destroy(Error('Oversized response'))});r.on('end',()=>{try{if(r.statusCode!==200)throw Error('TREN returned HTTP '+r.statusCode);resolve(withHeaders?{body:JSON.parse(raw),headers:r.headers}:JSON.parse(raw))}catch(e){reject(e)}})});req.on('timeout',()=>req.destroy(Error('TREN did not respond')));req.on('error',reject);req.end(body)})
}
function internal(url,base){try{const u=new URL(url);return u.origin===new URL(base).origin&&u.username===''&&u.password===''}catch{return false}}
function external(url){try{const u=new URL(url);return ['https:','http:'].includes(u.protocol)&&!u.username&&!u.password}catch{return false}}
module.exports={installId,validRoot,ready,request,internal,external};
