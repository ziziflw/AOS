"""Read-only delivery audit, plus deletion of explicitly owned synthetic credential receipts."""
import hashlib,importlib.metadata as md,json,sqlite3
from pathlib import Path
from boot import HERE,ROOT,read,write
from cleanup_credentials import cleanup

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
models=Path(read(HERE/'evidence/latest-models.json')['directory'])
host=Path(read(HERE/'evidence/latest-host.json')['directory'])
gui=Path(read(HERE/'evidence/latest-gui.json')['directory'])
checks=[]
for root in (models,host,gui):
    assert read(root/'summary.json')['passed']
    for p in root.rglob('run.sqlite'):
        db=sqlite3.connect('file:'+p.as_posix()+'?mode=ro',uri=True)
        try:
            assert db.execute('pragma integrity_check').fetchone()[0]=='ok'
            s=json.loads(db.execute('select state from snapshot where id=1').fetchone()[0]);seq=db.execute('select max(seq) from events').fetchone()[0]
            assert s['seq']==seq
            checks.append({'path':str(p.relative_to(HERE)),'runId':s['runId'],'state':s['state'],'sequence':seq,'integrity':'ok'})
        finally:db.close()
for name in ('anthropic-observed.json','json-observed.json','cancel-observed.json'):
    observed=read(gui/name)
    match=next(c for c in checks if c['runId']==observed['runId'])
    db=sqlite3.connect(HERE/match['path']);stored=json.loads(db.execute('select state from snapshot where id=1').fetchone()[0]);db.close()
    assert observed==stored, name+' UI/API vs independent SQLite mismatch'
baseline=read(ROOT/'planning/reuse-first-evidence/2026-10-29/protected-before.json')
changes=[];missing=[]
for name,expected in baseline.items():
    p=ROOT/name
    if not p.exists():missing.append(name)
    elif sha(p)!=expected:changes.append(name)
allowed={'experiments\\p0-03\\runtime.py','research\\README.md','research\\sources.md',
         'research\\04-model-adapters\\README.md','research\\10-feasibility-experiments\\README.md'}
assert not missing
assert set(changes)<=allowed, changes
manifest={}
for folder in (HERE,HERE/'frontend/src',HERE/'host/src'):
    for p in folder.iterdir():
        if p.is_file() and p.suffix in ('.py','.ps1','.cjs','.vue','.css','.js'):manifest[p.relative_to(HERE).as_posix()]=sha(p)
for name in ('fixtures/catalog.json','sdk-requirements.lock','frontend/package-lock.json','host/Cargo.lock','host/target/debug/host-window.exe','host/target/debug/host-probe.exe'):
    manifest[name]=sha(HERE/name)
for file,expected in read(gui/'build-files.json').items():assert manifest[file]==expected, 'GUI build identity drift'
inventory=[{'name':d.metadata['Name'],'version':d.version} for d in md.distributions()]
deps=read(HERE/'evidence/dependency-review.json');supplements=read(HERE/'evidence/supplemental-source-licenses.json')
for row in deps:
    assert row['sha256'] in {sha(p) for p in (HERE/'wheelhouse').glob('*.whl')}
    assert row['legal'] or any(s['name']==row['name'] and s['version']==row['version'] and s['files'] for s in supplements)
for row in supplements:
    assert sha(HERE/'source-archives'/row['url'].split('/')[-1])==row['sha256']
assert read(HERE/'evidence/process-check.json')['matchingOwnedExperimentProcesses']==0
size=sum(p.stat().st_size for p in (HERE/'.venv').rglob('*') if p.is_file())
report={'passed':True,'models':str(models),'host':str(host),'gui':str(gui),'sqliteRuns':checks,'uiSnapshotsExactlyEqualToSQLite':3,
  'oldProtectedFiles':len(baseline),'changedProtectedFiles':changes,'missingProtectedFiles':missing,
  'sourceAndBuildHashes':manifest,'distributions':sorted(inventory,key=lambda d:d['name'].lower()),'venvBytes':size,
  'deletedOwnedFixtureCredentials':cleanup(),'paidProviderCalls':0,
  'limits':['No supplier inference/billing verified','No clean-machine packaging or Linux/macOS proof','No OS sandbox claim']}
write(HERE/'evidence/delivery-audit.json',report)
print(json.dumps({k:report[k] for k in ('passed','oldProtectedFiles','changedProtectedFiles','uiSnapshotsExactlyEqualToSQLite','venvBytes')},ensure_ascii=False))
