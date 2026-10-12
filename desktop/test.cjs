'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),http=require('node:http'),path=require('node:path');
const r=require('./runtime.cjs');
test('only the selected, compatible installation is ready',()=>{const root=path.resolve('fixture');const body={application:'TREN',installation:r.installId(root),version:'0.10.0'};assert(r.ready(root,body));assert(!r.ready(root,{...body,version:'0.8.4'}));assert(!r.ready(root,{...body,installation:'other'}));assert(!r.ready(root,{...body,application:'unrelated'}))});
test('renderer navigation cannot reach foreign origins or privileged schemes',()=>{assert(r.internal('http://127.0.0.1:8765/api/state','http://127.0.0.1:8765'));for(const url of ['file:///C:/private','javascript:alert(1)','http://127.0.0.1:9999','https://evil.example','http://user@127.0.0.1:8765'])assert(!r.internal(url,'http://127.0.0.1:8765'));assert(r.external('https://example.com'));assert(!r.external('file:///C:/private'));assert(!r.external('https://user:secret@example.com'))});
test('backend transport uses loopback and sends control credentials only on stop',async()=>{const seen=[];const server=http.createServer((req,res)=>{seen.push({method:req.method,path:req.url,token:req.headers['x-tren-desktop']});req.resume();res.setHeader('Content-Type','application/json');res.end(JSON.stringify({ok:true}))});await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));try{const port=server.address().port;await r.request(port);await r.request(port,'POST','/api/desktop/stop','synthetic');assert.equal(seen[0].token,undefined);assert.equal(seen[1].token,'synthetic');assert.equal(seen[1].path,'/api/desktop/stop')}finally{server.close()}});

test('desktop and backend versions match',()=>assert.equal(require('./package.json').version,require('../version.json').version));

test('fresh bootstrap supplies runtimes without replacing existing backend data',()=>{
 const fs=require('node:fs'),os=require('node:os');const temp=fs.mkdtempSync(path.join(os.tmpdir(),'tren-bootstrap-'));
 try{const resources=path.join(temp,'resources'),home=path.join(temp,'home');
 for(const dir of ['backend','python','node'])fs.mkdirSync(path.join(resources,dir),{recursive:true});
 fs.writeFileSync(path.join(resources,'backend','app.py'),'original backend');fs.writeFileSync(path.join(resources,'python','python314._pth'),'original path');fs.writeFileSync(path.join(resources,'python','python.exe'),'fixture');fs.writeFileSync(path.join(resources,'node','node.exe'),'fixture');
 const prepare=require('./bootstrap.cjs').prepare;const first=prepare(home,resources,null,'0.10.0',false);
 assert(fs.existsSync(first.python));assert(fs.existsSync(first.node));assert(fs.readFileSync(path.join(path.dirname(first.python),'python314._pth'),'utf8').includes(first.root));
 fs.writeFileSync(path.join(first.root,'private-note.txt'),'keep me');fs.writeFileSync(path.join(first.root,'app.py'),'updated backend');
 prepare(home,resources,first.root,'0.10.0',false);
 assert.equal(fs.readFileSync(path.join(first.root,'app.py'),'utf8'),'updated backend');assert.equal(fs.readFileSync(path.join(first.root,'private-note.txt'),'utf8'),'keep me');
 }finally{fs.rmSync(temp,{recursive:true,force:true})}
});

// The rename must not create a new Chromium profile or leave the managed backend behind.
test('rebrand reuses legacy desktop profiles in place',()=>{
 const fs=require('node:fs'),os=require('node:os'),pick=require('./profile.cjs').legacyProfile;
 const temp=fs.mkdtempSync(path.join(os.tmpdir(),'veyra-profile-'));
 try{assert.equal(pick(temp),path.join(temp,'tren-desktop'));
  fs.mkdirSync(path.join(temp,'TREN'));fs.writeFileSync(path.join(temp,'TREN','installation.json'),'{}');
  assert.equal(pick(temp),path.join(temp,'TREN'));
  fs.mkdirSync(path.join(temp,'tren-desktop'));fs.writeFileSync(path.join(temp,'tren-desktop','installation.json'),'{}');
  assert.equal(pick(temp),path.join(temp,'tren-desktop'));
 }finally{fs.rmSync(temp,{recursive:true,force:true})}
});


test('packaged backend upgrade preserves real SQLite and private files',{skip:process.platform!=='win32'||!require('node:fs').existsSync(path.join(__dirname,'resources','backend','update-manifest.json'))},()=>{
 const fs=require('node:fs'),os=require('node:os'),crypto=require('node:crypto'),{spawnSync}=require('node:child_process');
 const temp=fs.mkdtempSync(path.join(os.tmpdir(),'veyra-upgrade-')),root=path.join(temp,'existing'),resources=path.join(__dirname,'resources');
 try{
  fs.mkdirSync(path.join(root,'data'),{recursive:true});fs.writeFileSync(path.join(root,'app.py'),'previous backend');fs.writeFileSync(path.join(root,'version.json'),JSON.stringify({version:'0.10.0'}));
  for(const name of ['pairing-code.txt','chatgpt-auth.json','private-settings.json'])fs.writeFileSync(path.join(root,'data',name),'private fixture '+name);
  const python=process.env.TREN_TEST_PYTHON||'python',db=path.join(root,'data','assistant.sqlite');
  const result=spawnSync(python,['-c',"import sqlite3,sys; c=sqlite3.connect(sys.argv[1]); c.execute('CREATE TABLE memories(content TEXT)'); c.execute(\"INSERT INTO memories VALUES('retained memory')\"); c.commit(); c.close()",db],{encoding:'utf8',windowsHide:true});assert.equal(result.status,0,result.stderr);
  const before=crypto.createHash('sha256').update(fs.readFileSync(db)).digest('hex');
  const prepared=require('./bootstrap.cjs').prepare(path.join(temp,'home'),resources,root,require('./package.json').version,false);
  assert.equal(prepared.root,root);assert.equal(fs.readFileSync(path.join(root,'app.py'),'utf8'),fs.readFileSync(path.join(resources,'backend','app.py'),'utf8'));
  assert.equal(crypto.createHash('sha256').update(fs.readFileSync(db)).digest('hex'),before);
  for(const name of ['pairing-code.txt','chatgpt-auth.json','private-settings.json'])assert.equal(fs.readFileSync(path.join(root,'data',name),'utf8'),'private fixture '+name);
  const backups=fs.readdirSync(path.join(root,'backups'));assert.equal(backups.length,1);assert.equal(fs.readFileSync(path.join(root,'backups',backups[0],'code','app.py'),'utf8'),'previous backend');
 }finally{fs.rmSync(temp,{recursive:true,force:true})}
});
