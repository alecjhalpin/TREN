"""Stage clean backend and hash-verified official Windows runtimes for packaging."""
from pathlib import Path
import hashlib,json,shutil,urllib.request,zipfile,gzip
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from build_release import build
ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/'desktop'/'resources'
DEST.mkdir(exist_ok=True)
manifest=build(ROOT,DEST/'backend.zip')
shutil.rmtree(DEST/'backend',ignore_errors=True)
with zipfile.ZipFile(DEST/'backend.zip') as z:
    for name in manifest['files']:
        path=DEST/'backend'/name;path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(z.read('Tren-Local/'+name))
(DEST/'backend'/'update-manifest.json').write_text(json.dumps(manifest))
def download(url,name,digest):
    target=DEST/name
    with urllib.request.urlopen(urllib.request.Request(url,headers={'Accept-Encoding':'identity'}),timeout=120) as response:
        raw=response.read(150*1024*1024)
        target.write_bytes(gzip.decompress(raw) if response.headers.get('Content-Encoding')=='gzip' else raw)
    if hashlib.sha256(target.read_bytes()).hexdigest()!=digest:raise ValueError('Runtime hash mismatch: '+name)
    return target
python=download('https://www.python.org/ftp/python/3.14.8/python-3.14.8-embed-amd64.zip','python.zip','a93abe456ab01bd96d7a085b3cdb6566b3063f4241360d114142fbdb07f0a310')
with zipfile.ZipFile(python) as z:z.extractall(DEST/'python')
node_name='node-v24.21.0-win-x64.zip'
with urllib.request.urlopen(urllib.request.Request('https://nodejs.org/dist/v24.21.0/SHASUMS256.txt',headers={'Accept-Encoding':'identity'}),timeout=30) as response:
    raw=response.read();sums=(gzip.decompress(raw) if response.headers.get('Content-Encoding')=='gzip' else raw).decode()
digest=next(line.split()[0] for line in sums.splitlines() if line.split()[-1]==node_name)
node=download('https://nodejs.org/dist/v24.21.0/'+node_name,'node.zip',digest)
with zipfile.ZipFile(node) as z:
    for item in z.infolist():
        if item.is_dir():continue
        name=Path(*Path(item.filename).parts[1:])
        if name.is_absolute() or '..' in name.parts:raise ValueError('Unexpected runtime path')
        target=DEST/'node'/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(z.read(item))
print('Staged backend, Python 3.14.8 and Node 24.21.0 with verified download hashes.')

# Ship the locked Playwright and CPU voice runtime; models download only after opt-in.
import subprocess
tool_runtime=DEST/'tool-runtime'
shutil.rmtree(tool_runtime,ignore_errors=True)
shutil.copytree(ROOT/'runtime',tool_runtime,ignore=shutil.ignore_patterns('node_modules','test.mjs'))
npm=DEST/'node'/'node_modules'/'npm'/'bin'/'npm-cli.js'
subprocess.run([str(DEST/'node'/'node.exe'),str(npm),'ci','--omit=dev','--ignore-scripts'],cwd=tool_runtime,check=True)

# Keep Windows x64 CPU libraries; voice uses no CUDA provider.
onnx=tool_runtime/'node_modules'/'onnxruntime-node'/'bin'/'napi-v3'
for platform in ('linux','darwin'):shutil.rmtree(onnx/platform,ignore_errors=True)
shutil.rmtree(onnx/'win32'/'arm64',ignore_errors=True)
for cuda in (onnx/'win32'/'x64').glob('*cuda*'):cuda.unlink()
print('Staged locked Windows browser/voice dependencies and bundled npm.')
