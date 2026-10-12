'use strict';
const {app,BrowserWindow,Menu,Tray,nativeImage,dialog,shell,clipboard,session}=require('electron');
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),{spawn}=require('node:child_process');
const runtime=require('./runtime.cjs');
const smoke=process.argv.includes('--smoke-test');
let win,tray,root,configPath,token='',quitting=false,stopping=false,updateBusy=false;
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
async function report(e){await dialog.showMessageBox({type:'error',title:'TREN needs attention',message:String(e.message||e),detail:'Your TREN installation and data were not reinstalled. Check the selected folder and data/updates/desktop.log if startup failed.'})}
function saveConfig(){fs.mkdirSync(path.dirname(configPath),{recursive:true});fs.writeFileSync(configPath,JSON.stringify({root}),{mode:0o600})}
async function chooseRoot(){const selected=await dialog.showOpenDialog({title:'Select your existing Tren-Local folder',properties:['openDirectory']});if(selected.canceled)return null;const picked=selected.filePaths[0];if(!runtime.validRoot(picked))throw Error('Choose the existing Tren-Local folder containing app.py, index.html and version.json.');return picked}
async function start(){
 if(process.platform!=='win32'&&!smoke)throw Error('This desktop build targets Windows.');
 if(!Number.isInteger(port)||port<1024||port>65535)throw Error('Invalid TREN port.');
 configPath=path.join(app.getPath('userData'),'installation.json');
 try{root=JSON.parse(fs.readFileSync(configPath,'utf8')).root}catch{}
 if(smoke)root=process.env.TREN_DESKTOP_ROOT;
 if(!root||!runtime.validRoot(root))root=path.join(app.getPath('desktop'),'Tren-Local');
 if(!runtime.validRoot(root))root=await chooseRoot();
 if(!root){quitting=true;app.quit();return}
 root=fs.realpathSync(root);saveConfig();
 await ensureBackend();
 session.defaultSession.setPermissionRequestHandler((wc,permission,callback)=>callback(false));
 session.defaultSession.setPermissionCheckHandler(()=>false);
 win=new BrowserWindow({width:1160,height:820,minWidth:700,minHeight:520,title:'TREN',icon:trayIcon(),show:false,backgroundColor:'#18191b',webPreferences:{nodeIntegration:false,contextIsolation:true,sandbox:true,webSecurity:true}});
 win.webContents.setWindowOpenHandler(({url})=>{if(runtime.external(url))shell.openExternal(url).catch(report);return {action:'deny'}});
 win.webContents.on('will-navigate',(e,url)=>{if(!runtime.internal(url,base)){e.preventDefault();if(runtime.external(url))shell.openExternal(url).catch(report)}});
 win.on('close',e=>{if(!quitting){e.preventDefault();win.hide()}});
 win.webContents.on('did-fail-load',(_e,code,_description,url)=>{if(code!==-3&&runtime.internal(url,base)&&!quitting)setTimeout(()=>win.loadURL(base).catch(()=>{}),1500)});
 Menu.setApplicationMenu(Menu.buildFromTemplate([{label:'TREN',submenu:[{label:'Open TREN',click:show},{label:'Show pairing code',click:()=>pairing().catch(report)},{label:'Open installation folder',click:()=>shell.openPath(root).then(error=>{if(error)throw Error(error)}).catch(report)},{label:'Check desktop updates',click:()=>desktopUpdate().catch(report)},{type:'separator'},{label:'Quit TREN',click:()=>quitDesktop().catch(report)}]},{label:'View',submenu:[{role:'reload'},{role:'resetZoom'},{role:'zoomIn'},{role:'zoomOut'},{role:'togglefullscreen'}]}]));
 tray=new Tray(trayIcon());tray.setToolTip('TREN — your personal AI agent');tray.on('double-click',show);refreshTray();
 await win.loadURL(base);if(!smoke)win.show();
 if(smoke)await smokeTest();
}
function trayIcon(){const size=32,pixels=Buffer.alloc(size*size*4);for(let y=0;y<size;y++)for(let x=0;x<size;x++){const d=Math.hypot(x-15.5,y-15.5);if(d<12){const i=(y*size+x)*4;pixels[i]=184;pixels[i+1]=240;pixels[i+2]=209;pixels[i+3]=255;if(d<5){pixels[i]=24;pixels[i+1]=25;pixels[i+2]=27}}}return nativeImage.createFromBitmap(pixels,{width:size,height:size})}
function refreshTray(){tray.setContextMenu(Menu.buildFromTemplate([{label:'Open TREN',click:show},{label:'Show pairing code',click:()=>pairing().catch(report)},{label:'Launch at Windows sign-in',type:'checkbox',checked:app.getLoginItemSettings().openAtLogin,enabled:app.isPackaged&&process.platform==='win32',click:item=>{app.setLoginItemSettings({openAtLogin:item.checked,path:process.execPath});refreshTray()}},{label:'Check desktop updates',click:()=>desktopUpdate().catch(report)},{type:'separator'},{label:'Quit TREN',click:()=>quitDesktop().catch(report)}]))}
async function ensureBackend(){
 let current;try{current=await runtime.request(port)}catch{}
 if(current){if(!runtime.ready(root,current))throw Error('A different or older TREN installation is using this port. Update your selected installation to v0.9.0 or later, then close its old app before starting desktop TREN.');return}
 const version=JSON.parse(fs.readFileSync(path.join(root,'version.json'),'utf8')).version;
 if(!runtime.ready(root,{application:'TREN',installation:runtime.installId(root),version}))throw Error('Update your existing TREN to v0.9.0 or later through Settings → Updates before opening the desktop app.');
 token=crypto.randomBytes(32).toString('hex');
 const logs=path.join(root,'data','updates');fs.mkdirSync(logs,{recursive:true});const fd=fs.openSync(path.join(logs,'desktop.log'),'a');
 const executable=process.env.TREN_PYTHON||(process.platform==='win32'?'py':'python3');
 const args=executable==='py'?['-3',path.join(root,'app.py'),'--no-browser']:[path.join(root,'app.py'),'--no-browser'];
 const env={...process.env,TREN_DATA:path.join(root,'data'),TREN_PORT:String(port),TREN_DESKTOP_TOKEN:token};delete env.OPENAI_API_KEY;delete env.CODEX_API_KEY;
 let failed;try{const child=spawn(executable,args,{cwd:root,env,shell:false,windowsHide:true,detached:true,stdio:['ignore',fd,fd]});child.on('error',e=>{failed=e});child.unref()}finally{fs.closeSync(fd)}
 const deadline=Date.now()+30000;while(Date.now()<deadline){if(failed)throw Error('Python could not start. TREN requires the existing Python installation.');try{current=await runtime.request(port);if(runtime.ready(root,current)){const hash=crypto.createHash('sha256').update(token).digest('hex');if(current.controller!==hash)throw Error('Another TREN instance started first.');return}}catch(e){if(e.message==='Another TREN instance started first.')throw e}await sleep(300)}
 throw Error('TREN did not start within 30 seconds. Check data/updates/desktop.log in your installation.');
}
async function pairing(){const code=fs.readFileSync(path.join(root,'data','pairing-code.txt'),'utf8').trim();const result=await dialog.showMessageBox({title:'Pair this TREN window',message:'Your local pairing code',detail:code+'\n\nPaste this into the pairing screen. Remember this device to stay connected.',buttons:['Copy code','Close'],defaultId:1,cancelId:1});if(result.response===0)clipboard.writeText(code)}
async function stopOwned(){
 if(!token)return;let status;
 try{status=await runtime.request(port)}catch(e){if(e.code==='ECONNREFUSED')return;throw e}
 if(status.controller!==crypto.createHash('sha256').update(token).digest('hex'))throw Error('This desktop window no longer owns the backend. Close it separately.');
 await runtime.request(port,'POST','/api/desktop/stop',token);
 const deadline=Date.now()+15000;while(Date.now()<deadline){try{await runtime.request(port)}catch(e){if(e.code==='ECONNREFUSED')return}await sleep(100)}
 throw Error('TREN is still stopping. Wait and try Quit again.');
}
async function quitDesktop(){if(stopping||quitting)return;stopping=true;try{if(!smoke){const answer=await dialog.showMessageBox({type:'question',title:'Quit TREN?',message:token?'Quit TREN and stop its background work?':'Quit the desktop window?',detail:token?'Active tasks will be cancelled. Completed file changes remain.':'This window connected to an already-running backend. That backend will remain running.',buttons:['Keep running','Quit'],defaultId:0,cancelId:0});if(answer.response!==1)return}await stopOwned();quitting=true;tray?.destroy();app.quit()}finally{stopping=false}}
async function desktopUpdate(){if(updateBusy)return;if(!app.isPackaged){await dialog.showMessageBox({message:'Desktop updates are available in the installed Windows app.'});return}updateBusy=true;try{const {autoUpdater}=require('electron-updater');if(!autoUpdater.listenerCount('error'))autoUpdater.on('error',()=>{});autoUpdater.autoDownload=false;autoUpdater.autoInstallOnAppQuit=false;autoUpdater.logger=null;const update=await autoUpdater.checkForUpdates();if(!update||update.updateInfo.version===app.getVersion()){await dialog.showMessageBox({message:'Your desktop app is up to date.'});return}const answer=await dialog.showMessageBox({message:'Download desktop '+update.updateInfo.version+'?',detail:'Backend updates remain in TREN Settings. Desktop updates replace only this window and launcher.',buttons:['Later','Download'],defaultId:0,cancelId:0});if(answer.response!==1)return;await autoUpdater.downloadUpdate();const install=await dialog.showMessageBox({message:'Install the desktop update and restart?',detail:'Active work in a backend owned by this desktop window will be cancelled. Completed changes remain.',buttons:['Later','Install & restart'],defaultId:0,cancelId:0});if(install.response===1){await stopOwned();quitting=true;autoUpdater.quitAndInstall(false,true)}}finally{updateBusy=false}}
async function smokeTest(){
 await win.webContents.executeJavaScript(`document.getElementById('themePreference').value='light';document.getElementById('themePreference').dispatchEvent(new Event('change'));if(document.documentElement.dataset.theme!=='light')throw Error('Light theme failed')`);
 await new Promise((resolve,reject)=>{const timeout=setTimeout(()=>reject(Error('Reload timeout')),15000);win.webContents.once('did-finish-load',()=>{clearTimeout(timeout);resolve()});win.reload()});
 const mode=await win.webContents.executeJavaScript('document.documentElement.dataset.theme');if(mode!=='light')throw Error('Theme did not survive reload');
 await win.webContents.executeJavaScript(`document.getElementById('themePreference').value='dark';document.getElementById('themePreference').dispatchEvent(new Event('change'));if(document.documentElement.dataset.theme!=='dark')throw Error('Dark theme failed')`);
 const output=path.join(__dirname,'smoke-output');fs.mkdirSync(output,{recursive:true});
 const code=fs.readFileSync(path.join(root,'data','pairing-code.txt'),'utf8').trim();
 await win.webContents.executeJavaScript(`(async()=>{await fetch('/api/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({code:${JSON.stringify(code)},remember:true,name:'Desktop smoke fixture'})});await refresh()})()`);
 for(const theme of ['light','dark']){
  await win.webContents.executeJavaScript(`applyTheme('${theme}');current.messages=[{role:'user',content:'Hey TREN, what can we work on?',created:1},{role:'assistant',provider:'chatgpt',content:'Ready when you are.\\n\\n- **Talk through an idea**\\n- Work on your PC\\n- Build something together',created:2}];renderConversation();hideError();document.getElementById('health').textContent='Layout preview'`);
  await sleep(350);const screenshot=await win.webContents.capturePage();fs.writeFileSync(path.join(output,'TREN-Desktop-'+theme+'.png'),screenshot.toPNG());
 }
 await stopOwned();quitting=true;tray?.destroy();app.exit(0);
}
