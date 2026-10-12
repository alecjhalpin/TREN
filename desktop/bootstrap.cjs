'use strict';
const fs=require('node:fs'),path=require('node:path'),{spawnSync}=require('node:child_process');
function prepare(home,resources,root,version,preferExisting=true){
 const managed=path.join(home,'backend');
 if(!root){root=managed;if(!fs.existsSync(path.join(root,'app.py'))){fs.mkdirSync(root,{recursive:true});fs.cpSync(path.join(resources,'backend'),root,{recursive:true,errorOnExist:true,force:false})}}
 const runtime=path.join(home,'runtime-'+version);fs.mkdirSync(runtime,{recursive:true});
 for(const name of ['python','node']){const dest=path.join(runtime,name);if(!fs.existsSync(dest)){const temp=dest+'.staging';fs.rmSync(temp,{recursive:true,force:true});fs.cpSync(path.join(resources,name),temp,{recursive:true});fs.renameSync(temp,dest)}}
 const pyRoot=path.join(runtime,'python');const pth=fs.readdirSync(pyRoot).find(name=>/^python\d+\._pth$/.test(name));
 if(!pth||/[\r\n]/.test(root))throw Error('Invalid bundled Python configuration');
 fs.writeFileSync(path.join(pyRoot,pth),'python314.zip\n.\n'+path.resolve(root)+'\nimport site\n');
 const source=path.join(resources,'backend'),manifestPath=path.join(source,'update-manifest.json');
 if(fs.existsSync(manifestPath)&&fs.existsSync(path.join(root,'version.json'))){
  const next=JSON.parse(fs.readFileSync(manifestPath,'utf8')).version,current=JSON.parse(fs.readFileSync(path.join(root,'version.json'),'utf8')).version;
  const parts=v=>v.split('.').map(Number);const a=parts(next),b=parts(current);const newer=a.some((n,i)=>n>b[i]&&a.slice(0,i).every((v,j)=>v===b[j]));
  if(newer){const result=spawnSync(path.join(pyRoot,'python.exe'),['-c','import sys; sys.path.insert(0,sys.argv[1]); import upgrade; upgrade.upgrade(sys.argv[2])',source,root],{encoding:'utf8',timeout:120000,windowsHide:true,shell:false});if(result.status!==0)throw Error('Backend upgrade failed. Existing data retained. '+(result.stderr||result.error?.message||''));}
 }
 const tools=path.join(home,'tools');fs.mkdirSync(tools,{recursive:true});
 let python=path.join(pyRoot,'python.exe'),args=[];
 for(const command of preferExisting?['py','python']:[]){const prefix=command==='py'?['-3']:[];const probe=spawnSync(command,[...prefix,'-c','import sys; assert sys.version_info >= (3,11); print(sys.executable)'],{encoding:'utf8',timeout:5000,windowsHide:true,shell:false});if(probe.status===0&&fs.existsSync((probe.stdout||'').trim())){python=probe.stdout.trim();break}}
 return {root,python,args,node:path.join(runtime,'node','node.exe'),npm:path.join(runtime,'node','node_modules','npm','bin','npm-cli.js'),npx:path.join(runtime,'node','node_modules','npm','bin','npx-cli.js'),toolRuntime:path.join(resources,'tool-runtime'),tools};
}
module.exports={prepare};
