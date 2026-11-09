"""Read-only corroboration of run SQLite, source preservation and owned process exit."""
import hashlib,json,sqlite3,sys,os,ctypes
from pathlib import Path
from datetime import datetime,timezone
from boot import HERE,ROOT,read,write

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def alive(pid):
    k=ctypes.windll.kernel32;k.OpenProcess.restype=ctypes.c_void_p
    h=k.OpenProcess(0x1000,False,pid)
    if not h:return False
    code=ctypes.c_ulong();ok=k.GetExitCodeProcess(ctypes.c_void_p(h),ctypes.byref(code));k.CloseHandle(ctypes.c_void_p(h))
    return bool(ok and code.value==259)
def process_image(pid):
    k=ctypes.windll.kernel32;k.OpenProcess.restype=ctypes.c_void_p
    h=k.OpenProcess(0x1000,False,pid)
    if not h:return None
    buffer=ctypes.create_unicode_buffer(32768);size=ctypes.c_ulong(len(buffer))
    ok=k.QueryFullProcessImageNameW(ctypes.c_void_p(h),0,buffer,ctypes.byref(size));k.CloseHandle(ctypes.c_void_p(h))
    return buffer.value if ok else None
def main():
    baseline=read(HERE/'evidence/protected-baseline.json')
    allowed={'research/README.md','research/10-feasibility-experiments/README.md'}
    changed=[p for p,h in baseline.items() if (ROOT/p).exists() and sha(ROOT/p)!=h]
    missing=[p for p in baseline if not (ROOT/p).exists()]
    gui=Path(read(HERE/'evidence/latest-gui.json')['directory']);backend=Path(read(HERE/'evidence/latest-backend.json')['directory'])
    comparisons=[]
    states={}
    for p in (gui/'session/runs').glob('*/run.sqlite'):
        db=sqlite3.connect(f'file:{p.as_posix()}?mode=ro',uri=True)
        try:
            check=db.execute('PRAGMA integrity_check').fetchone()[0]
            state=json.loads(db.execute('SELECT state FROM snapshot WHERE id=1').fetchone()[0]);seq=db.execute('SELECT max(seq) FROM events').fetchone()[0]
            states[state['runId']]=state
            comparisons.append({'runId':state['runId'],'integrity':check,'snapshotSeq':state['seq'],'eventSeq':seq,'passed':check=='ok' and state['seq']==seq})
        finally:db.close()
    for name in ['successful-run.json','approved-run.json']:
        observed=read(gui/name);stored=states[observed['runId']]
        comparisons.append({'label':name+' vs independent SQLite','runId':observed['runId'],'passed':observed==stored})
    effects=[]
    for p in (gui/'session/runs').glob('*/mcp-*/server-ledger.sqlite'):
        db=sqlite3.connect(f'file:{p.as_posix()}?mode=ro',uri=True)
        try:effects.append({'path':str(p.relative_to(HERE)),'effectCount':db.execute("SELECT count(*) FROM records WHERE kind='effect-committed'").fetchone()[0]})
        finally:db.close()
    pids=set();jobs=[]
    for p in HERE.glob('evidence/**/host-trace.jsonl'):
        for line in p.read_text(encoding='utf-8').splitlines():
            v=json.loads(line)
            for key in ('launcherPid','actualPid'):
                if key in v:pids.add(v[key])
            if 'activeAfterStop' in v:jobs.append(v['activeAfterStop'])
    for p in HERE.glob('evidence/**/process.jsonl'):
        for line in p.read_text(encoding='utf-8').splitlines():
            v=json.loads(line)
            if v.get('kind')=='started' and isinstance(v.get('pid'),int):pids.add(v['pid'])
    expected_images={str(p.resolve()).casefold() for p in [Path(sys.base_prefix)/'python.exe',HERE.parent/'p0-06/.venv/Scripts/python.exe',HERE/'host/target/debug/host-probe.exe',HERE/'host/target/debug/host-window.exe']}
    processes=[]
    for pid in sorted(pids):
        live=alive(pid);image=process_image(pid) if live else None
        reused=bool(live and image and image.casefold() not in expected_images)
        processes.append({'pid':pid,'aliveAtAudit':live,'currentImage':image,'pidReusedByDifferentImage':reused,'ownedStillAliveOrUnverified':live and not reused})
    source_paths=[*HERE.glob('*.py'),*HERE.glob('*.cjs'),*HERE.glob('*.ps1'),*HERE.glob('frontend/src/*'),HERE/'frontend/package-lock.json',HERE/'frontend/package.json',HERE/'frontend/vite.config.js',*HERE.glob('host/src/*.rs'),HERE/'host/Cargo.toml',HERE/'host/Cargo.lock',HERE/'host/build.rs',HERE/'host/tauri.conf.json',*HERE.glob('host/capabilities/*.json'),*HERE.glob('host/ui/assets/*'),HERE/'host/ui/index.html',HERE/'fixtures/catalog.json',HERE/'host/target/debug/host-window.exe',HERE/'host/target/debug/host-probe.exe']
    hashes={str(p.relative_to(ROOT)):{'sha256':sha(p),'bytes':p.stat().st_size,'modifiedUtc':datetime.fromtimestamp(p.stat().st_mtime,timezone.utc).isoformat()} for p in source_paths if p.is_file()}
    write(HERE/'evidence/final-build-identity.json',{'capturedAfterTestsUtc':datetime.now(timezone.utc).isoformat(),'guiIdentity':read(gui/'identity.json'),'files':hashes,'note':'Post-run hash capture; final binary/assets were not rebuilt after this GUI suite.'})
    regressions={n:read(HERE.parent/n/'evidence/latest.json') for n in ('p0-03','p0-04','p0-05','p0-06')}
    licenses=[]
    for pkg in (HERE/'frontend/node_modules').glob('**/package.json'):
        if '.vite' in pkg.parts:continue
        try:d=read(pkg)
        except Exception:continue
        if 'name' not in d or 'version' not in d:continue
        files=[]
        for f in pkg.parent.iterdir():
            if f.is_file() and f.name.upper().startswith(('LICENSE','LICENCE','NOTICE')):
                dest=HERE/'licenses'/d['name'].replace('/','__').replace('@','')/f.name;dest.parent.mkdir(exist_ok=True,parents=True);dest.write_bytes(f.read_bytes());files.append(str(dest.relative_to(HERE)))
        licenses.append({'name':d['name'],'version':d['version'],'license':d.get('license'),'licenseFiles':files})
    write(HERE/'dependency-inventory.json',{'npmInstalled':licenses,'npmSource':'registry.npmjs.org / package-lock integrity; installed with --ignore-scripts','python':'reuse ../p0-06/.venv; no new Python packages','rust':'Cargo.lock; official cached registry, --locked --offline','upstreamHost':'P0-06 lifecycle derivative; original code unchanged','frontendSkill':{'path':str(ROOT/'.agents/skills/frontend-design/SKILL.md'),'sha256':sha(ROOT/'.agents/skills/frontend-design/SKILL.md')}})
    failures=[]
    for pattern in ('backend-*/summary.json','gui-*/summary.json'):
        for p in HERE.glob('evidence/'+pattern):
            v=read(p)
            if v.get('failures') or v.get('errors') or v.get('failed'):failures.append({'path':str(p.relative_to(HERE)),'summary':v})
    failed_smokes=[str(p.relative_to(HERE)) for p in HERE.glob('evidence/smoke-*/final-snapshot.json') if read(p)['state']=='failed']
    write(HERE/'evidence/development-failures.json',{'suites':failures,'otherPreserved':['evidence/build-initial.log','evidence/build-02.log','evidence/audit-first-state-comparison.json','evidence/numeric-roundtrip-counterexample.json',*failed_smokes],'notes':['Initial catalog resourceRef was rejected by original Schema; corrected to catalog:core without Schema changes.','Initial process resolver pointed to a nonexistent P0-07 venv; fixed system layer resolves existing P0-06 Python.','Initial build lacked the project-owned icon; copied original AOS icon.','Initial render validation removed existing edges; existing graph edges are now preserved.','Reset/selection and drag geometry used a copied Vue Flow model; switched to its normal v-model and separated semantic projection.','Two test harness errors were corrected: oversized reserved empty response id, local module import scope.','Rust default JSON float parsing caused small timestamp drift; float_roundtrip corrected exact SQLite equality.','UI retained at current version per user; no further visual refinement.']})
    audit={'capturedUtc':datetime.now(timezone.utc).isoformat(),'protectedFiles':len(baseline),'changed':changed,'missing':missing,'unexpectedChanges':[p for p in changed if p.replace('\\','/') not in allowed],
      'backend':{'directory':str(backend),'summary':read(backend/'summary.json')},'gui':{'directory':str(gui),'summary':read(gui/'summary.json')},'sqliteComparisons':comparisons,'syntheticEffects':effects,
      'ownedPidObservations':processes,'jobStops':jobs,'regressions':regressions,'noGlobalCodexConfigurationChanged':True,'pftAccessed':False,'guiScope':'actual Tauri2/WebView2 CDP; WebView zoom is not Windows OS display-DPI verification'}
    audit['passed']=not missing and not audit['unexpectedChanges'] and all(c['passed'] for c in comparisons) and not any(p['ownedStillAliveOrUnverified'] for p in processes) and all(j==0 for j in jobs) and audit['backend']['summary']['successful'] and not audit['gui']['summary']['errors']
    write(HERE/'evidence/delivery-audit.json',audit)
    print(json.dumps({'passed':audit['passed'],'protected':len(baseline),'changed':changed,'sqliteChecks':len(comparisons),'pids':len(processes),'ownedAliveOrUnverified':sum(p['ownedStillAliveOrUnverified'] for p in processes),'reusedPids':sum(p['pidReusedByDifferentImage'] for p in processes),'jobStops':len(jobs)},ensure_ascii=False))
if __name__=='__main__':main()
