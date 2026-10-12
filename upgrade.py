"""One-time bootstrap and manual recovery. Installed app handles future ZIP updates."""
import argparse
import json
import os
from pathlib import Path
from update_runtime import install,rollback as restore,allowed,version


def upgrade(target):
    source=Path(__file__).resolve().parent;target=Path(target).resolve()
    if target==source or not (target/'app.py').is_file() or not (target/'data').is_dir():raise ValueError('Choose your existing TREN installation, not this update folder.')
    m=json.loads((source/'update-manifest.json').read_text());version(m['version'])
    if not isinstance(m.get('files'),dict) or not all(allowed(n) for n in m['files']):raise ValueError('Invalid manifest.')
    # Existing installer keeps default data unchanged. In-app updater honors TREN_DATA too.
    b=install(target,source,m,target/'data');print('Updated your existing TREN folder:',target);print('Backup:',b)
    print('Rollback: py -3 "'+str(source/'upgrade.py')+'" --rollback "'+str(b)+'"');return b


def rollback(backup):
    b=Path(backup).resolve();restore(b.parent.parent,b);print('Previous code restored. Current data retained.')


def choose_target():
    home=Path.home();candidates=[home/'Desktop/Tren-Local',home/'OneDrive/Desktop/Tren-Local',home/'Tren-Local']
    matches=[p for p in candidates if (p/'app.py').is_file() and (p/'data').is_dir()]
    if len(matches)==1:return matches[0]
    try:
        import tkinter as tk
        from tkinter import filedialog
        win=tk.Tk();win.withdraw();choice=filedialog.askdirectory(title='Select your existing Tren-Local folder');win.destroy()
        if choice:return choice
        raise ValueError('Update cancelled.')
    except ImportError:return input('Existing TREN folder: ').strip().strip('"')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('target',nargs='?');p.add_argument('--rollback');a=p.parse_args()
    try:
        if a.rollback:rollback(a.rollback)
        else:
            print('Close TREN before this one-time updater installation. No dependencies are installed.')
            upgrade(a.target or choose_target())
    except Exception as exc:print('Update failed:',exc);raise SystemExit(1)
