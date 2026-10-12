"""Create a manifest-verified, personal-data-free TREN release asset."""
from pathlib import Path
import hashlib
import json
import zipfile
from update_runtime import allowed,REQUIRED,version


def build(root,output):
    root=Path(root);v=json.loads((root/'version.json').read_text())['version'];version(v)
    paths=[p for p in root.rglob('*') if p.is_file() and allowed(p.relative_to(root).as_posix()) and '__pycache__' not in p.parts]
    files={p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}
    if not REQUIRED.issubset(files):raise ValueError('Release source incomplete.')
    manifest={'format':1,'version':v,'files':files}
    (root/'update-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as z:
        for p in paths:z.write(p,'Tren-Local/'+p.relative_to(root).as_posix())
        z.write(root/'update-manifest.json','Tren-Local/update-manifest.json')
    return manifest

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('output');a=p.parse_args();build(Path(__file__).resolve().parent,a.output)
