'use strict';
const {app,BrowserWindow,Menu,Tray,nativeImage,dialog,shell,clipboard,session,ipcMain}=require('electron');
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),{spawn}=require('node:child_process');
const runtime=require('./runtime.cjs');
// Retain the pre-rebrand profile before Chromium or the instance lock initializes.
const profile=require('./profile.cjs').legacyProfile(app.getPath('appData'));
fs.mkdirSync(profile,{recursive:true});app.setPath('userData',profile);app.setPath('sessionData',profile);
const smoke=process.argv.includes('--smoke-test');
let win,tray,root,previousRoot,configPath,toolchain,setupBusy=false,token='',quitting=false,stopping=false,updateBusy=false;
const fresh=process.argv.includes('--smoke-fresh');
const port=Number(process.env.TREN_PORT||8765),base='http://127.0.0.1:'+port;
const sleep=ms=>new Promise(resolve=>setTimeout(resolve,ms));
if(!app.requestSingleInstanceLock()){app.quit()}else{
 app.on('second-instance',()=>show());
 app.on('activate',()=>show());
 app.on('window-all-closed',()=>{});
 app.on('before-quit',e=>{if(!quitting){e.preventDefault();quitDesktop().catch(report)}});
 app.whenReady().then(start).catch(async e=>{if(smoke){console.error(e);app.exit(1)}else{await report(e);quitting=true;app.quit()}});
}
function show(){if(win){if(win.isMinimized())win.restore();win.show();win.focus()}}
async function report(e){await dialog.showMessageBox({type:'error',title:'VEYRA needs attention',message:String(e.message||e),detail:'Your VEYRA installation and data were not reinstalled. Check the selected folder and data/updates/desktop.log if startup failed.'})}
function saveConfig(){fs.mkdirSync(path.dirname(configPath),{recursive:true});fs.writeFileSync(configPath,JSON.stringify({root}),{mode:0o600})}
async function chooseRoot(){const selected=await dialog.showOpenDialog({title:'Select your existing Tren-Local folder',properties:['openDirectory']});if(selected.canceled)return null;const picked=selected.filePaths[0];if(!runtime.validRoot(picked))throw Error('Choose the existing Tren-Local folder containing app.py, index.html and version.json.');return picked}
async function start(){
 if(process.platform!=='win32'&&!smoke)throw Error('This desktop build targets Windows.');
 if(!Number.isInteger(port)||port<1024||port>65535)throw Error('Invalid VEYRA port.');
 configPath=path.join(app.getPath('userData'),'installation.json');
 try{root=JSON.parse(fs.readFileSync(configPath,'utf8')).root;previousRoot=root}catch{}
 if(smoke)root=fresh?null:process.env.TREN_DESKTOP_ROOT;
 if(!fresh&&(!root||!runtime.validRoot(root)))root=path.join(app.getPath('desktop'),'Tren-Local');
 const resources=process.env.TREN_RESOURCES||process.resourcesPath;
 if(fs.existsSync(path.join(resources,'backend','app.py'))){
  const packagedVersion=JSON.parse(fs.readFileSync(path.join(resources,'backend','version.json'),'utf8')).version;
  if(runtime.validRoot(root)&&JSON.parse(fs.readFileSync(path.join(root,'version.json'),'utf8')).version!==packagedVersion){const running=await runtime.request(port).catch(()=>null);if(running)throw Error('Close the running VEYRA backend before upgrading this installation.');}
  const home=fresh?path.join(__dirname,'managed-smoke'):path.join(app.getPath('userData'),'managed');
  if(fresh)fs.rmSync(home,{recursive:true,force:true});
  toolchain=require('./bootstrap.cjs').prepare(home,resources,runtime.validRoot(root)?root:null,app.getVersion(),!fresh);root=toolchain.root;
  if(fresh)toolchain.python=path.join(home,'runtime-'+app.getVersion(),'python','python.exe');
 }else if(!root||!runtime.validRoot(root))root=await chooseRoot();
 if(!root){quitting=true;app.quit();return}
 root=fs.realpathSync(root);saveConfig();
 await ensureBackend();
 session.defaultSession.setPermissionRequestHandler((wc,permission,callback,details)=>{const local=runtime.internal(details.requestingUrl||wc.getURL(),base);callback(local&&(permission==='media'&&details.mediaTypes?.length>0&&details.mediaTypes.every(type=>type==='audio')||permission==='notifications'))});
 session.defaultSession.setPermissionCheckHandler((wc,permission,origin,details)=>runtime.internal(origin,base)&&(permission==='media'&&details.mediaType==='audio'||permission==='notifications'));
 win=new BrowserWindow({width:1160,height:820,minWidth:700,minHeight:520,title:'VEYRA',titleBarStyle:'hidden',titleBarOverlay:{color:'#18191b',symbolColor:'#f1f1ee',height:38},icon:trayIcon(),show:false,backgroundColor:'#18191b',webPreferences:{nodeIntegration:false,contextIsolation:true,sandbox:true,webSecurity:true,preload:path.join(__dirname,'preload.cjs')}});
 win.webContents.setWindowOpenHandler(({url})=>{if(runtime.external(url))shell.openExternal(url).catch(report);return {action:'deny'}});
 win.webContents.on('will-navigate',(e,url)=>{if(!runtime.internal(url,base)){e.preventDefault();if(runtime.external(url))shell.openExternal(url).catch(report)}});
 win.on('close',e=>{if(!quitting){e.preventDefault();win.hide()}});
 win.webContents.on('did-fail-load',(_e,code,_description,url)=>{if(code!==-3&&runtime.internal(url,base)&&!quitting)setTimeout(()=>win.loadURL(base).catch(()=>{}),1500)});
 const nativeMenu=Menu.buildFromTemplate([{label:'VEYRA',submenu:[{label:'Open VEYRA',click:show},{label:'Show pairing code',click:()=>pairing().catch(report)},{label:'Open installation folder',click:()=>shell.openPath(root).then(error=>{if(error)throw Error(error)}).catch(report)},{label:'Check desktop updates',click:()=>desktopUpdate().catch(report)},{type:'separator'},{label:'Quit VEYRA',click:()=>quitDesktop().catch(report)}]},{label:'View',submenu:[{role:'reload'},{role:'resetZoom'},{role:'zoomIn'},{role:'zoomOut'},{role:'togglefullscreen'}]}]);Menu.setApplicationMenu(null);
 ipcMain.on('chrome-menu',event=>{if(runtime.internal(event.senderFrame?.url,base))nativeMenu.popup({window:win})});
 ipcMain.on('chrome-theme',(event,mode)=>{if(runtime.internal(event.senderFrame?.url,base)&&['light','dark'].includes(mode))win.setTitleBarOverlay({color:mode==='light'?'#f7f8fa':'#18191b',symbolColor:mode==='light'?'#182228':'#f1f1ee',height:38})});
 ipcMain.handle('unified-update',(event)=>{if(!runtime.internal(event.senderFrame?.url,base))throw Error('Local update only');return desktopUpdate()});
 ipcMain.handle('optional-setup',(event,feature)=>{if(!runtime.internal(event.senderFrame?.url,base))throw Error('Local setup only');return optionalSetup(feature)});
 tray=new Tray(trayIcon());tray.setToolTip('VEYRA — Your AI. Your computer. Your rules.');tray.on('double-click',show);refreshTray();
 await autoPair();await win.loadURL(base);win.show();
 if(smoke)await smokeTest();
}
function trayIcon(){const icon=nativeImage.createFromPath(path.join(__dirname,'assets','veyra-icon.png'));if(icon.isEmpty())throw Error('VEYRA icon is missing.');return icon.resize({width:32,height:32})}
function refreshTray(){tray.setContextMenu(Menu.buildFromTemplate([{label:'Open VEYRA',click:show},{label:'Show pairing code',click:()=>pairing().catch(report)},{label:'Launch at Windows sign-in',type:'checkbox',checked:app.getLoginItemSettings().openAtLogin,enabled:app.isPackaged&&process.platform==='win32',click:item=>{app.setLoginItemSettings({openAtLogin:item.checked,path:process.execPath});refreshTray()}},{label:'Check desktop updates',click:()=>desktopUpdate().catch(report)},{type:'separator'},{label:'Quit VEYRA',click:()=>quitDesktop().catch(report)}]))}
async function ensureBackend(){
 let current;try{current=await runtime.request(port)}catch{}
 if(current){if(!runtime.ready(root,current))throw Error('A different or older VEYRA installation is using this port. Update your selected installation to v0.10.0 or later, then close its old app before starting desktop VEYRA.');return}
 const version=JSON.parse(fs.readFileSync(path.join(root,'version.json'),'utf8')).version;
 if(!runtime.ready(root,{application:'TREN',installation:runtime.installId(root),version}))throw Error('Update your existing VEYRA to v0.10.0 or later through Settings → Updates before opening the desktop app.');
 token=crypto.randomBytes(32).toString('hex');
 const logs=path.join(root,'data','updates');fs.mkdirSync(logs,{recursive:true});const fd=fs.openSync(path.join(logs,'desktop.log'),'a');
 const executable=(fresh?toolchain?.python:process.env.TREN_PYTHON)||toolchain?.python||(process.platform==='win32'?'py':'python3');
 const args=executable==='py'?['-3',path.join(root,'app.py'),'--no-browser']:[path.join(root,'app.py'),'--no-browser'];
 const env={...process.env,TREN_NODE:toolchain?.node||process.env.TREN_NODE||'',VEYRA_TOOLS_ROOT:toolchain?.toolRuntime||'',VEYRA_NPM_CLI:toolchain?.npm||'',VEYRA_NPX_CLI:toolchain?.npx||'',PATH:toolchain?[path.dirname(toolchain.node),toolchain.tools,process.env.PATH].join(path.delimiter):process.env.PATH,TREN_DATA:path.join(root,'data'),TREN_PORT:String(port),TREN_DESKTOP_TOKEN:token};delete env.OPENAI_API_KEY;delete env.CODEX_API_KEY;
 let failed;try{const child=spawn(executable,args,{cwd:root,env,shell:false,windowsHide:true,detached:true,stdio:['ignore',fd,fd]});child.on('error',e=>{failed=e});child.unref()}finally{fs.closeSync(fd)}
 const deadline=Date.now()+30000;while(Date.now()<deadline){if(failed)throw Error('Python could not start. VEYRA requires the existing Python installation.');try{current=await runtime.request(port);if(runtime.ready(root,current)){const hash=crypto.createHash('sha256').update(token).digest('hex');if(current.controller!==hash)throw Error('Another VEYRA instance started first.');return}}catch(e){if(e.message==='Another VEYRA instance started first.')throw e}await sleep(300)}
 throw Error('VEYRA did not start within 30 seconds. Check data/updates/desktop.log in your installation.');
}
async function autoPair(){
 if((await session.defaultSession.cookies.get({url:base,name:'hp_session'})).length){if(typeof previousRoot==='string'&&runtime.installId(previousRoot)===runtime.installId(root))return;await session.defaultSession.cookies.remove(base,'hp_session')}
 const code=fs.readFileSync(path.join(root,'data','pairing-code.txt'),'utf8').trim();
 const response=await runtime.request(port,'POST','/api/login','',{code,remember:true,name:'Desktop app'},true);
 const cookie=(response.headers['set-cookie']||[]).find(value=>value.startsWith('hp_session='));const value=cookie?.match(/^hp_session=([A-Za-z0-9_-]{32,128});/)?.[1];
 if(!value)throw Error('Desktop pairing did not complete.');
 await session.defaultSession.cookies.set({url:base,name:'hp_session',value,httpOnly:true,sameSite:'strict',expirationDate:Date.now()/1000+90*86400});
}
async function optionalSetup(feature){
 if(!['codex','codex-login','ollama'].includes(feature)||!toolchain)throw Error('Use the full desktop installer for optional tool setup.');
 if(setupBusy)throw Error('Another setup step is running.');
 const answer=await dialog.showMessageBox({message:feature==='ollama'?'Set up local AI?':feature==='codex'?'Install Codex coding tools?':'Connect Codex with ChatGPT?',detail:feature==='ollama'?'Installs Ollama if missing and downloads qwen3:8b (about 5 GB). Windows may show an installer/UAC prompt.':feature==='codex'?'Downloads the official @openai/codex package into this app’s private tools folder. Existing global installations are left in place.':'Opens the normal Codex browser sign-in. Finish it in your browser.',buttons:['Cancel','Continue'],defaultId:0,cancelId:0});if(answer.response!==1)return {message:'Setup cancelled.'};
 setupBusy=true;
 const run=(exe,args)=>new Promise((resolve,reject)=>{const log=fs.openSync(path.join(root,'data','updates','tool-setup.log'),'a');let child;try{child=spawn(exe,args,{shell:false,windowsHide:true,env:{...process.env,PATH:[path.dirname(toolchain.node),toolchain.tools,process.env.PATH].join(path.delimiter)},stdio:['ignore',log,log]})}finally{fs.closeSync(log)}const timeout=setTimeout(()=>{child.kill();reject(Error('Setup timed out; inspect tool-setup.log before retrying.'))},1800000);child.on('error',e=>{clearTimeout(timeout);reject(e)});child.on('exit',code=>{clearTimeout(timeout);code===0?resolve():reject(Error('Setup failed. See the private data/updates/tool-setup.log.'))})});
 try{
  const found=process.platform==='win32'?require('node:child_process').spawnSync('where.exe',['codex'],{encoding:'utf8',windowsHide:true,timeout:5000}):null;
  const globalCli=found?.status===0?(found.stdout||'').trim().split(/\r?\n/)[0]:null;
  if(feature==='codex'&&globalCli)return {message:'Codex is already installed. You can connect it with ChatGPT.'};
  if(feature==='codex'){const script=path.join(toolchain.tools,'node_modules','@openai','codex','bin','codex.js');if(!fs.existsSync(script))await run(toolchain.node,[toolchain.npm,'install','--global','--prefix',toolchain.tools,'@openai/codex@0.162.1']);return {message:'Codex is installed. Connect it with ChatGPT next.'}}
  if(feature==='codex-login'){if(globalCli&&path.extname(globalCli).toLowerCase()==='.exe')await run(globalCli,['login']);else{const script=globalCli?path.join(path.dirname(globalCli),'node_modules','@openai','codex','bin','codex.js'):path.join(toolchain.tools,'node_modules','@openai','codex','bin','codex.js');await run(toolchain.node,[script,'login'])}return {message:'Codex sign-in finished. Check Codex under Tools to verify.'}}
  let exe=path.join(process.env.LOCALAPPDATA,'Programs','Ollama','ollama.exe');const foundOllama=require('node:child_process').spawnSync('where.exe',['ollama'],{encoding:'utf8',windowsHide:true,timeout:5000});const existingOllama=foundOllama.status===0?(foundOllama.stdout||'').trim().split(/\r?\n/)[0]:null;if(existingOllama&&fs.existsSync(existingOllama))exe=existingOllama;
  if(!fs.existsSync(exe)){await run('winget',['install','--id','Ollama.Ollama','--exact','--source','winget','--accept-package-agreements','--accept-source-agreements']);if(!fs.existsSync(exe))throw Error('Open Ollama after installation, then retry local setup. If winget is unavailable, install from ollama.com/download/windows.')}
  let tags=await runtime.request(11434,'GET','/api/tags').catch(()=>null);
  if(!tags){const server=spawn(exe,['serve'],{shell:false,windowsHide:true,detached:true,stdio:'ignore',env:{...process.env,OLLAMA_NO_CLOUD:'1'}});server.on('error',()=>{});server.unref();const deadline=Date.now()+20000;while(Date.now()<deadline&&!tags){await sleep(500);tags=await runtime.request(11434,'GET','/api/tags').catch(()=>null)}}
  if(!tags)throw Error('Ollama did not start. Open Ollama and retry local setup.');
  if(!(tags.models||[]).some(model=>model.name==='qwen3:8b'))await run(exe,['pull','qwen3:8b']);return {message:'Local AI is ready. Select Ollama under conversation preferences when you want local chat.'};
 }finally{setupBusy=false}
}
async function pairing(){const code=fs.readFileSync(path.join(root,'data','pairing-code.txt'),'utf8').trim();const result=await dialog.showMessageBox({title:'Pair this VEYRA window',message:'Your local pairing code',detail:code+'\n\nPaste this into the pairing screen. Remember this device to stay connected.',buttons:['Copy code','Close'],defaultId:1,cancelId:1});if(result.response===0)clipboard.writeText(code)}
async function stopOwned(){
 if(!token)return;let status;
 try{status=await runtime.request(port)}catch(e){if(e.code==='ECONNREFUSED')return;throw e}
 if(status.controller!==crypto.createHash('sha256').update(token).digest('hex'))throw Error('This desktop window no longer owns the backend. Close it separately.');
 await runtime.request(port,'POST','/api/desktop/stop',token);
 const deadline=Date.now()+15000;while(Date.now()<deadline){try{await runtime.request(port)}catch(e){if(e.code==='ECONNREFUSED')return}await sleep(100)}
 throw Error('VEYRA is still stopping. Wait and try Quit again.');
}
async function quitDesktop(){if(setupBusy)throw Error('Finish the optional tool setup before quitting. Closing the window keeps setup running in the tray.');if(stopping||quitting)return;stopping=true;try{if(!smoke){const answer=await dialog.showMessageBox({type:'question',title:'Quit VEYRA?',message:token?'Quit VEYRA and stop its background work?':'Quit the desktop window?',detail:token?'Active tasks will be cancelled. Completed file changes remain.':'This window connected to an already-running backend. That backend will remain running.',buttons:['Keep running','Quit'],defaultId:0,cancelId:0});if(answer.response!==1)return}await stopOwned();quitting=true;tray?.destroy();app.quit()}finally{stopping=false}}
async function desktopUpdate(){if(updateBusy)return;if(!app.isPackaged){await dialog.showMessageBox({message:'Desktop updates are available in the installed Windows app.'});return}updateBusy=true;try{const {autoUpdater}=require('electron-updater');if(!autoUpdater.listenerCount('error'))autoUpdater.on('error',()=>{});autoUpdater.autoDownload=false;autoUpdater.autoInstallOnAppQuit=false;autoUpdater.logger=null;const update=await autoUpdater.checkForUpdates();if(!update||update.updateInfo.version===app.getVersion()){await dialog.showMessageBox({message:'Your desktop app is up to date.'});return}await autoUpdater.downloadUpdate();const install=await dialog.showMessageBox({message:'Install the VEYRA update and restart?',detail:'Active work in a backend owned by this desktop window will be cancelled. Completed changes remain.',buttons:['Later','Install & restart'],defaultId:0,cancelId:0});if(install.response===1){await stopOwned();quitting=true;autoUpdater.quitAndInstall(false,true)}}finally{updateBusy=false}}
async function smokeTest(){
 await win.webContents.executeJavaScript(`document.getElementById('themePreference').value='light';document.getElementById('themePreference').dispatchEvent(new Event('change'));if(document.documentElement.dataset.theme!=='light')throw Error('Light theme failed')`);
 await new Promise((resolve,reject)=>{const timeout=setTimeout(()=>reject(Error('Reload timeout')),15000);win.webContents.once('did-finish-load',()=>{clearTimeout(timeout);resolve()});win.reload()});
 const mode=await win.webContents.executeJavaScript('document.documentElement.dataset.theme');if(mode!=='light')throw Error('Theme did not survive reload');
 await win.webContents.executeJavaScript(`document.getElementById('themePreference').value='dark';document.getElementById('themePreference').dispatchEvent(new Event('change'));if(document.documentElement.dataset.theme!=='dark')throw Error('Dark theme failed')`);
 const output=path.join(__dirname,'smoke-output');fs.mkdirSync(output,{recursive:true});
 await win.webContents.executeJavaScript(`(async()=>{await refresh();if(!document.body.classList.contains('is-desktop'))throw Error('Desktop chrome missing')})()`);

 if(await win.webContents.executeJavaScript('!current.profile.onboarding_complete')){
  fs.writeFileSync(path.join(output,'VEYRA-Onboarding.png'),(await win.webContents.capturePage()).toPNG());
  await win.webContents.executeJavaScript(`(async()=>{document.getElementById('setupName').value='Nova';await document.getElementById('setupNameNext').onclick();if(current.profile.name!=='Nova'||setupStep!==2)throw Error('Name onboarding failed');document.getElementById('setupProviderLater').onclick();await document.getElementById('setupFinish').onclick();if(!current.profile.onboarding_complete)throw Error('Setup did not finish')})()`);
 }
 await win.webContents.executeJavaScript(`document.querySelector('[data-mode="agent"]').click();if(document.getElementById('route').value!=='agent')throw Error('Mode picker failed');document.querySelector('[data-mode="auto"]').click()`);

 const code=fs.readFileSync(path.join(root,'data','pairing-code.txt'),'utf8').trim();
 await win.webContents.executeJavaScript(`(async()=>{await fetch('/api/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({code:${JSON.stringify(code)},remember:true,name:'Desktop smoke fixture'})});await refresh()})()`);
 for(const theme of ['light','dark']){
  await win.webContents.executeJavaScript(`applyTheme('${theme}');current.messages=[{role:'user',content:'Hey Nova, what can we work on?',created:1},{role:'assistant',provider:'chatgpt',content:'Ready when you are.\\n\\n- **Talk through an idea**\\n- Work on your PC\\n- Build something together',created:2}];renderConversation();hideError();document.getElementById('health').textContent='Layout preview'`);
  await win.webContents.executeJavaScript(`new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))`);
  const background=await win.webContents.executeJavaScript(`getComputedStyle(document.body).backgroundColor`);if(background!==(theme==='light'?'rgb(247, 248, 250)':'rgb(24, 25, 27)'))throw Error('Rendered theme background failed: '+background);
  await sleep(350);const screenshot=await win.webContents.capturePage();fs.writeFileSync(path.join(output,'VEYRA-Desktop-'+theme+'.png'),screenshot.toPNG());
 }
 {await win.webContents.executeJavaScript(`document.getElementById('modePicker').open=true`);await sleep(150);fs.writeFileSync(path.join(output,'VEYRA-Mode-Menu.png'),(await win.webContents.capturePage()).toPNG())}
 await stopOwned();quitting=true;tray?.destroy();app.exit(0);
}
