#!/usr/bin/env python3
"""Non-destructive artifact transport; never resets or checks out a worktree.

Pull copies missing files only and reports differing existing files. Push uses a
private index and fast-forward commit-tree; requires explicit --include paths.
Live bootstrap artifacts are always protected. No JSONL is ever truncated.
"""
from __future__ import annotations
import argparse
import hashlib
import os
from pathlib import Path
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parents[1]


def git(*args,env=None,data=None):
    return subprocess.check_output(['git',*args],cwd=ROOT,env=env,input=data)


def safe_relative(path):
    p=Path(path)
    if p.is_absolute() or '..' in p.parts or not p.parts or p.parts[0]!='outputs':
        raise ValueError('Only relative outputs/ paths are allowed')
    if p.is_relative_to('outputs/rebuttal/profile_bootstrap'):
        raise ValueError('Bootstrap outputs are protected while independently owned workers run')
    return p


def pull(tip, includes=()):
    entries=git('ls-tree','-r','-z',tip,'--','outputs/').split(b'\0')
    copied=different=0
    for entry in entries:
        if not entry: continue
        meta,name=entry.split(b'\t',1); mode,kind,blob=meta.split()
        p=Path(os.fsdecode(name))
        if includes and not any(p == prefix or p.is_relative_to(prefix) for prefix in includes):
            continue
        # The invalid E1 recovery_v2 workflow must never be restored by transport.
        if p.is_relative_to('outputs/iclr/e1_dataset') and 'recovery_v2' in p.parts:
            continue
        if p.is_relative_to('outputs/rebuttal/profile_bootstrap'): continue
        safe_relative(str(p))
        if mode not in (b'100644',b'100755'): raise ValueError('Non-regular artifact')
        dest=ROOT/p
        if dest.exists():
            if git('hash-object',str(dest)).strip()!=blob: different+=1
            continue
        dest.parent.mkdir(parents=True,exist_ok=True)
        content=git('cat-file','blob',blob.decode())
        # Exclusive creation prevents racing a newly started writer.
        try:
            with dest.open('xb') as f: f.write(content)
            copied+=1
        except FileExistsError: pass
    print(f'pull: copied_missing={copied}, existing_differences_preserved={different}; bootstrap protected')


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('action',choices=['pull','push'])
    ap.add_argument('message',nargs='?',default='Jazz completed artifact snapshot')
    ap.add_argument('--include',action='append',default=[])
    args=ap.parse_args()
    git('fetch','origin','artifacts')
    tip=git('rev-parse','FETCH_HEAD').decode().strip()
    includes = [safe_relative(name) for name in args.include]
    pull(tip, includes)  # Scoped pull before push; existing local files are preserved.
    if args.action=='pull': return
    if not args.include: raise SystemExit('push requires --include for completed outputs only')
    paths=[]
    for name in args.include:
        p=ROOT/safe_relative(name)
        if not p.exists(): raise SystemExit(f'Missing artifact: {name}')
        paths.extend([p] if p.is_file() else sorted(x for x in p.rglob('*') if x.is_file()))
    with tempfile.TemporaryDirectory(prefix='jazz-index-') as tmp:
        env={**os.environ,'GIT_INDEX_FILE':str(Path(tmp)/'index')}
        git('read-tree',tip,env=env)
        for path in paths:
            if path.is_symlink(): raise ValueError('Symlink artifacts are not supported')
            relative=path.relative_to(ROOT)
            if path.name.startswith('.') or path.suffix=='.log': continue
            before=path.stat(); data=path.read_bytes(); after=path.stat()
            if (before.st_size,before.st_mtime_ns)!=(after.st_size,after.st_mtime_ns):
                raise RuntimeError(f'Active writer detected: {relative}')
            if path.suffix=='.jsonl' and data and not data.endswith(b'\n'):
                raise RuntimeError(f'Incomplete JSONL: {relative}')
            blob=git('hash-object','-w','--stdin',data=data).decode().strip()
            git('update-index','--add','--cacheinfo',f'100644,{blob},{relative}',env=env)
        tree=git('write-tree',env=env).decode().strip()
        old_tree=git('rev-parse',tip+'^{tree}').decode().strip()
        if tree==old_tree: print('No new artifacts'); return
        commit=git('commit-tree',tree,'-p',tip,data=(args.message+'\n').encode()).decode().strip()
        git('push','origin',commit+':refs/heads/artifacts')
        print('Published artifact commit',commit)


if __name__=='__main__': main()
