// VEYRA local tools. stdin/stdout is private JSON-RPC-like framing, never an HTTP service.
import readline from 'node:readline';
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {spawn} from 'node:child_process';
import {createRequire} from 'node:module';
import {fileURLToPath,pathToFileURL} from 'node:url';
const dependencies=createRequire(path.join(process.env.VEYRA_TOOLS_ROOT||path.dirname(fileURLToPath(import.meta.url)),'package.json'));
const dependency=async name=>{const m=await import(pathToFileURL(dependencies.resolve(name)).href);return m.default&&typeof m.default==='object'?{...m.default,...m}:m};
import {buildPageSnapshot} from './snapshot.mjs';
const data=path.resolve(process.env.VEYRA_DATA||'data'),requests=new Map(),browsers=new Map(),mcpPool=new Map();
let asrPromise,ttsPromise;
const safeId=x=>{if(typeof x!=='string'||!/^[-a-zA-Z0-9_]{1,64}$/.test(x))throw Error('Invalid profile or connection identifier');return x};
const bounded=x=>JSON.stringify(x).slice(0,180000);
const fingerprint=x=>crypto.createHash('sha256').update(JSON.stringify(x)).digest('hex');
const line=readline.createInterface({input:process.stdin,crlfDelay:Infinity});
const output=(id,result,error)=>process.stdout.write(JSON.stringify({id,...(error?{error:String(error.message||error).slice(0,3000)}:{result})})+'\n');
function check(signal){if(signal.aborted)throw Error('Cancelled')}
async function closeBrowser(key){const entry=browsers.get(key);browsers.delete(key);if(entry)await entry.context.close().catch(()=>{})}
async function browser(p,signal){
 const profile=safeId(p.profile||'default');check(signal);
 const options=p.options||{},action=p.action;
 if(action==='close'){await closeBrowser(profile);return {ok:true}}
 let entry=browsers.get(profile);
 if(!entry){
  const {chromium}=await dependency('playwright');const folder=path.join(data,'browser_profiles',profile);fs.mkdirSync(folder,{recursive:true});
  const launch={headless:p.headless!==false,acceptDownloads:true,viewport:{width:1280,height:850}};
  // Dedicated profile only. Existing Chrome/Edge cookies are never copied or silently attached.
  if(process.platform==='win32'&&!process.env.VEYRA_USE_CHROMIUM)launch.channel='msedge';
  const context=await chromium.launchPersistentContext(folder,launch);entry={context,tabs:new Map(),counter:0,console:[],network:[]};
  browsers.set(profile,entry);context.on('page',page=>registerPage(entry,page));for(const page of context.pages())registerPage(entry,page);
 }
 const onAbort=()=>closeBrowser(profile);signal.addEventListener('abort',onAbort,{once:true});
 try{
  check(signal);const tab=String(options.tab||'');let page=entry.tabs.get(tab)||[...entry.tabs.values()][0];
  if(!page||page.isClosed())page=registerPage(entry,await entry.context.newPage());
  page.setDefaultTimeout(Math.min(30000,Number(options.timeout_ms)||15000));
  const locator=()=>options.ref?page.locator('[data-veyra-ref='+JSON.stringify(String(options.ref))+']'):options.role?page.getByRole(options.role,{name:options.name,exact:options.exact!==false}):page.locator(String(options.selector||'body'));
  switch(action){
   case 'open':case 'navigate':{const url=new URL(options.url);if(!['http:','https:'].includes(url.protocol)||url.username||url.password)throw Error('Use a plain HTTP(S) URL');await page.goto(url.href,{waitUntil:'domcontentloaded',timeout:45000});break}
   case 'snapshot':return await snapshot(page,entry);
   case 'extract':return {url:page.url(),text:(await locator().innerText()).slice(0,30000)};
   case 'click':await locator().click();break;
   case 'fill':await locator().fill(String(options.text||''));break;
   case 'type':await locator().pressSequentially(String(options.text||''));break;
   case 'press':await locator().press(String(options.key||'Enter'));break;
   case 'select':await locator().selectOption(options.value);break;
   case 'check':await locator().setChecked(options.checked!==false);break;
   case 'hover':await locator().hover();break;
   case 'focus':await locator().focus();break;
   case 'scroll':await page.mouse.wheel(Number(options.x)||0,Number(options.y)||600);break;
   case 'wait':if(options.selector)await locator().waitFor({state:options.state||'visible'});else await page.waitForTimeout(Math.min(10000,Number(options.ms)||500));break;
   case 'back':await page.goBack({waitUntil:'domcontentloaded'});break;
   case 'forward':await page.goForward({waitUntil:'domcontentloaded'});break;
   case 'reload':await page.reload({waitUntil:'domcontentloaded'});break;
   case 'tabs':return {tabs:[...entry.tabs].filter(([,v])=>!v.isClosed()).map(([id,v])=>({id,url:v.url()}))};
   case 'new_tab':{const newPage=registerPage(entry,await entry.context.newPage());return {tab:[...entry.tabs].find(([,v])=>v===newPage)[0]}}
   case 'close_tab':await page.close();return {ok:true};
   case 'screenshot':{const dir=path.join(data,'projects',safeId(p.workspace||'default'),'screenshots');fs.mkdirSync(dir,{recursive:true});const file=path.join(dir,crypto.randomUUID()+'.png');await page.screenshot({path:file,fullPage:options.full_page!==false});return {file,url:page.url()}}
   case 'download':{const next=page.waitForEvent('download',{timeout:45000});await locator().click();const download=await next;const dir=path.join(data,'projects',safeId(p.workspace||'default'),'downloads');fs.mkdirSync(dir,{recursive:true});const file=path.join(dir,crypto.randomUUID()+'-'+path.basename(download.suggestedFilename()));await download.saveAs(file);return {file,error:await download.failure()}}
   case 'upload':{const file=path.resolve(String(options.path||''));if(!fs.statSync(file).isFile())throw Error('Choose an existing file');await locator().setInputFiles(file);break}
   case 'attribute':return {value:await locator().getAttribute(String(options.attribute||'href'))};
   case 'count':return {count:await locator().count()};
   case 'console':return {entries:entry.console.slice(-100)};
   case 'network':return {entries:entry.network.slice(-100)};
   case 'dialog':page.once('dialog',dialog=>options.accept?dialog.accept(String(options.text||'')):dialog.dismiss());return {ok:true,note:'Handler applies to the next page dialog'};
   default:throw Error('Unsupported browser operation');
  }
  check(signal);return await snapshot(page,entry);
 }finally{signal.removeEventListener('abort',onAbort)}
}
function registerPage(entry,page){if([...entry.tabs.values()].includes(page))return page;entry.tabs.set(String(++entry.counter),page);page.on('console',msg=>{entry.console.push({type:msg.type(),text:msg.text().slice(0,1000)});if(entry.console.length>100)entry.console.shift()});page.on('requestfinished',r=>{entry.network.push({method:r.method(),url:r.url().slice(0,1000)});if(entry.network.length>100)entry.network.shift()});return page}
async function snapshot(page,entry){
 const elements=await page.locator('body').evaluate(body=>[...body.querySelectorAll('a,button,input,textarea,select,h1,h2,h3,[role]')].slice(0,300).map((e,i)=>{e.setAttribute('data-veyra-ref','e'+i);return ({role:e.getAttribute('role')||({A:'link',BUTTON:'button',INPUT:e.type==='checkbox'?'checkbox':'textbox',TEXTAREA:'textbox',SELECT:'combobox',H1:'heading',H2:'heading',H3:'heading'}[e.tagName]||'element'),name:(e.getAttribute('aria-label')||e.labels?.[0]?.innerText||e.innerText||e.getAttribute('placeholder')||'').slice(0,160),ref:'e'+i,disabled:!!e.disabled,checked:!!e.checked,value:e.type==='password'?'[password omitted]':(e.value||'').slice(0,100),selector:e.id?'#'+CSS.escape(e.id):e.tagName.toLowerCase()+':nth-of-type('+([...e.parentElement.children].filter(v=>v.tagName===e.tagName).indexOf(e)+1)+')'})}));
 const result=buildPageSnapshot(page.url(),await page.title(),elements);result.text=result.text.slice(0,30000);result.tab=[...entry.tabs].find(([,v])=>v===page)?.[0];return result;
}
class MCPConnection{
 constructor(config){this.config=config;this.counter=0;this.waiters=new Map();this.last=Date.now();this.session=null;this.version='2025-11-25'}
 async start(signal){
  if(this.config.transport==='stdio'){
   let command=this.config.command,args=this.config.args||[];
   if(['npm','npx'].includes(command)&&process.env.VEYRA_NPM_CLI){args=[command==='npx'?process.env.VEYRA_NPX_CLI:process.env.VEYRA_NPM_CLI,...args];command=process.execPath}
   this.proc=spawn(command,args,{cwd:this.config.cwd||data,env:{...process.env,...this.config.env},shell:false,windowsHide:true,stdio:['pipe','pipe','pipe']});
   this.proc.stderr.resume();this.proc.on('error',error=>this.fail(error));this.proc.on('exit',()=>this.fail(Error('MCP process ended')));
   const rl=readline.createInterface({input:this.proc.stdout,crlfDelay:Infinity});rl.on('line',line=>{if(line.length>2*1024*1024)return this.close();try{this.receive(JSON.parse(line))}catch{}});
  }
  const initial=await this.rpc('initialize',{protocolVersion:this.version,capabilities:{},clientInfo:{name:'VEYRA',version:'0.12.0'}},signal);
  this.version=initial.protocolVersion||this.version;await this.notify('notifications/initialized',{});
  this.tools=(await this.rpc('tools/list',{},signal)).tools||[];
 }
 receive(packet){if(packet.method==='notifications/tools/list_changed')this.toolsDirty=true;if(packet.id!==undefined){const item=this.waiters.get(packet.id);if(item){this.waiters.delete(packet.id);packet.error?item.reject(Error(packet.error.message||'MCP error')):item.resolve(packet.result)}}}
 fail(error){for(const item of this.waiters.values())item.reject(error);this.waiters.clear()}
 packet(method,params,id){return {jsonrpc:'2.0',...(id===undefined?{}:{id}),method,params:{...params,_meta:{'io.modelcontextprotocol/protocolVersion':this.version,'io.modelcontextprotocol/clientCapabilities':{}}}}}
 async notify(method,params){const packet=this.packet(method,params);if(this.proc)this.proc.stdin.write(JSON.stringify(packet)+'\n');else await this.http(packet,new AbortController().signal)}
 async rpc(method,params,signal){
  check(signal);this.last=Date.now();const id=++this.counter,packet=this.packet(method,params,id);
  if(!this.proc)return this.http(packet,signal);
  return new Promise((resolve,reject)=>{const timer=setTimeout(()=>{this.waiters.delete(id);reject(Error('MCP request timed out'))},60000);const done=()=>{clearTimeout(timer);signal.removeEventListener('abort',abort)};const abort=()=>{this.notify('notifications/cancelled',{requestId:id}).catch(()=>{});this.waiters.delete(id);done();reject(Error('MCP cancelled'))};this.waiters.set(id,{resolve:v=>{done();resolve(v)},reject:e=>{done();reject(e)}});signal.addEventListener('abort',abort,{once:true});this.proc.stdin.write(JSON.stringify(packet)+'\n')});
 }
 async http(packet,signal){
  const url=new URL(this.config.url);if(!['https:','http:'].includes(url.protocol)||url.username||url.password)throw Error('Invalid MCP endpoint');
  const headers={...this.config.headers,'Content-Type':'application/json',Accept:'application/json, text/event-stream','MCP-Protocol-Version':this.version};if(this.session)headers['Mcp-Session-Id']=this.session;
  const response=await fetch(url,{method:'POST',headers,body:JSON.stringify(packet),signal,redirect:'error'});
  if(!response.ok)throw Error('MCP HTTP '+response.status);this.session=response.headers.get('mcp-session-id')||this.session;if(response.status===202||response.status===204)return {};
  if(response.headers.get('content-type')?.includes('text/event-stream')){
   const reader=response.body.getReader(),decoder=new TextDecoder();let buffer='',total=0;
   try{while(true){const {value,done}=await reader.read();if(done)break;total+=value.length;if(total>2*1024*1024)throw Error('Oversized MCP response');buffer=(buffer+decoder.decode(value,{stream:true})).replaceAll('\r\n','\n');let index;while((index=buffer.indexOf('\n\n'))>=0){const event=buffer.slice(0,index).replaceAll('\r','');buffer=buffer.slice(index+2);const raw=event.split('\n').filter(v=>v.startsWith('data:')).map(v=>v.slice(5).trim()).join('\n');if(raw){const packetOut=JSON.parse(raw);if(packetOut.id===packet.id){if(packetOut.error)throw Error(packetOut.error.message);return packetOut.result}}}}}finally{await reader.cancel().catch(()=>{})}throw Error('MCP stream ended without response');
  }
  const reader=response.body.getReader(),chunks=[];let size=0;try{while(true){const {value,done}=await reader.read();if(done)break;size+=value.length;if(size>2*1024*1024)throw Error('Oversized MCP response');chunks.push(Buffer.from(value))}}finally{await reader.cancel().catch(()=>{})}const result=JSON.parse(Buffer.concat(chunks).toString('utf8'));if(result.error)throw Error(result.error.message);return result.result;
 }
 async close(){this.fail(Error('MCP connection closed'));if(this.proc){this.proc.kill();this.proc=null}if(this.session){await fetch(this.config.url,{method:'DELETE',headers:{...this.config.headers,'Mcp-Session-Id':this.session,'MCP-Protocol-Version':this.version},signal:AbortSignal.timeout(3000)}).catch(()=>{})}}
}
async function mcp(params,signal){const key=safeId(params.id),fp=fingerprint(params.config);let entry=mcpPool.get(key);if(entry&&entry.fingerprint!==fp){await entry.connection.close();mcpPool.delete(key);entry=null}if(!entry){const connection=new MCPConnection(params.config);entry={connection,fingerprint:fp,ready:connection.start(signal)};mcpPool.set(key,entry);try{await entry.ready}catch(error){mcpPool.delete(key);await connection.close();throw error}}else await entry.ready;check(signal);if(params.operation==='list'||entry.connection.toolsDirty){entry.connection.tools=(await entry.connection.rpc('tools/list',{},signal)).tools||[];entry.connection.toolsDirty=false;if(params.operation==='list')return {tools:entry.connection.tools,protocol:entry.connection.version};}if(params.operation==='call'){if(!entry.connection.tools.some(t=>t.name===params.tool))throw Error('MCP tool not advertised by server');return entry.connection.rpc('tools/call',{name:params.tool,arguments:params.arguments||{}},signal)}if(params.operation==='close'){await entry.connection.close();mcpPool.delete(key);return {ok:true}}throw Error('Invalid MCP operation')}
// Transformers 3.x closes its cache stream asynchronously. Windows native ONNX
// can briefly reject a freshly cached file while that writer is still closing.
// Retry only model initialization with this specific sharing error, never tools.
async function loadLocalModel(factory){
 for(let attempt=0;;attempt++){try{return await factory()}catch(error){if(process.platform!=='win32'||attempt>=2||!String(error.message).includes('system error number 13'))throw error;await new Promise(resolve=>setTimeout(resolve,500))}}
}
async function voice(params,signal){
 const cache=path.join(data,'voice_models');
 const loadASR=()=>{if(!asrPromise){asrPromise=(async()=>{const {pipeline,env}=await dependency('@huggingface/transformers');env.cacheDir=cache;return loadLocalModel(()=>pipeline('automatic-speech-recognition','onnx-community/whisper-base',{dtype:'q8',device:'cpu'}))})();asrPromise.catch(()=>asrPromise=null)}return asrPromise};
 const loadTTS=()=>{if(!ttsPromise){ttsPromise=(async()=>{const {KokoroTTS}=await dependency('kokoro-js');return loadLocalModel(()=>KokoroTTS.from_pretrained('onnx-community/Kokoro-82M-v1.0-ONNX',{dtype:'q8',device:'cpu'}))})();ttsPromise.catch(()=>ttsPromise=null)}return ttsPromise};
 if(params.operation==='prepare'){await loadASR();check(signal);await loadTTS();check(signal);return {ready:true,model:'Whisper base + Kokoro · local CPU'}};
 if(params.operation==='voices'){const tts=await loadTTS();return {voices:tts.voices}};
 if(params.operation==='speak'){
  const tts=await loadTTS();check(signal);const text=String(params.text||'').slice(0,1800);if(!text.trim())throw Error('Supply text to speak');
  const audio=await tts.generate(text,{voice:params.voice||'af_heart',speed:Math.min(1.5,Math.max(.7,Number(params.rate)||1))});check(signal);
  const pcm=audio.audio,rate=audio.sampling_rate||24000,wav=Buffer.alloc(44+pcm.length*2);wav.write('RIFF',0);wav.writeUInt32LE(wav.length-8,4);wav.write('WAVEfmt ',8);wav.writeUInt32LE(16,16);wav.writeUInt16LE(1,20);wav.writeUInt16LE(1,22);wav.writeUInt32LE(rate,24);wav.writeUInt32LE(rate*2,28);wav.writeUInt16LE(2,32);wav.writeUInt16LE(16,34);wav.write('data',36);wav.writeUInt32LE(pcm.length*2,40);for(let i=0;i<pcm.length;i++)wav.writeInt16LE(Math.round(Math.max(-1,Math.min(1,pcm[i]))*32767),44+i*2);
  return {wav:wav.toString('base64'),model:'Kokoro',local:true};
 }
 const recognizer=await loadASR();check(signal);const bytes=Buffer.from(params.pcm||'','base64');if(bytes.length<640||bytes.length>16000*4*120||bytes.length%4)throw Error('Voice recording must be under 120 seconds at 16 kHz float32');
 const audio=new Float32Array(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength));if(audio.some(v=>!Number.isFinite(v)||Math.abs(v)>1.1))throw Error('Invalid microphone audio');
 const result=await recognizer(audio,{chunk_length_s:30,stride_length_s:5,...(params.language?{language:params.language,task:'transcribe'}:{})});check(signal);return {text:result.text,model:'Whisper base',local:true};
}
async function stopAll(){for(const controller of requests.values())controller.abort();for(const key of browsers.keys())await closeBrowser(key);for(const entry of mcpPool.values())await entry.connection.close();mcpPool.clear()}
line.on('line',async text=>{let packet;try{if(text.length>12*1024*1024)throw Error('Oversized tool packet');packet=JSON.parse(text);const {id,method,params={}}=packet;if(method==='cancel'){requests.get(params.request_id)?.abort();return output(id,{ok:true})}if(method==='stop_all'){await stopAll();return output(id,{ok:true})}const controller=new AbortController();requests.set(id,controller);try{const result=method==='browser'?await browser(params,controller.signal):method==='mcp'?await mcp(params,controller.signal):method==='voice'?await voice(params,controller.signal):method==='health'?{node:process.version,browsers:browsers.size,mcp:mcpPool.size}:null;if(result===null)throw Error('Unknown local tool');output(id,result)}finally{requests.delete(id)}}catch(error){output(packet?.id,error?null:undefined,error)}});
line.on('close',async()=>{await stopAll();process.exit(0)});
setInterval(()=>{for(const [id,entry] of mcpPool)if(Date.now()-entry.connection.last>15*60000){entry.connection.close();mcpPool.delete(id)}},60000).unref();
