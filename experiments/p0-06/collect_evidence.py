"""Dependency/build inventory and delivery audit; does not change authoritative run records."""
import hashlib,importlib.metadata as md,json,os,platform,re,sqlite3,subprocess,sys,tomllib
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def write(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def size(p,exclude=()):return sum(x.stat().st_size for x in p.rglob('*') if x.is_file() and not any(t in x.parts for t in exclude))
def main():
    packages=[];lock=[];wheelroots=[HERE.parent/'p0-04/wheelhouse',HERE.parent/'p0-05/wheelhouse'];wheels={}
    for wh in wheelroots:
        for p in wh.glob('*.whl'):
            parts=p.name.split('-');wheels.setdefault((parts[0].replace('_','-').lower(),parts[1]),[]).append(p)
    for d in sorted(md.distributions(),key=lambda d:d.metadata['Name'].lower()):
        name=d.metadata['Name'];version=d.version
        if name.lower()=='pip':continue
        artifacts=wheels.get((name.replace('_','-').lower(),version),[])
        hashes=sorted({sha(p) for p in artifacts})
        packages.append({'name':name,'version':version,'license':d.metadata.get('License-Expression') or d.metadata.get('License'),'wheels':[{'path':str(p.relative_to(ROOT)),'sha256':sha(p),'bytes':p.stat().st_size} for p in artifacts]})
        if not hashes:raise RuntimeError('Unrecorded artifact '+name)
        lock.append(name+'=='+version+' '+' '.join('--hash=sha256:'+h for h in hashes))
    (HERE/'requirements.lock').write_text('\n'.join(lock)+'\n',encoding='utf-8')
    write(HERE/'dependency-inventory.json',packages)
    cargo=tomllib.loads((HERE/'host/Cargo.lock').read_text());crates=[]
    src=Path.home()/'.cargo/registry/src'
    for package in cargo['package']:
        record={k:package[k] for k in ('name','version','checksum') if k in package}
        candidates=list(src.glob('*/'+package['name']+'-'+package['version']+'/Cargo.toml'))
        if candidates:
            manifest=tomllib.loads(candidates[0].read_text());record['license']=manifest.get('package',{}).get('license');record['manifestSha256']=sha(candidates[0])
        record['sourceDownloaded']=bool(candidates);crates.append(record)
    write(HERE/'rust-dependency-inventory.json',crates)
    env={'date':'2026-10-27','platform':platform.platform(),'machine':platform.machine(),'python':sys.version,'basePrefix':sys.base_prefix,'sqlite':sqlite3.sqlite_version,
        'rustc':subprocess.check_output(['rustc','--version'],text=True).strip(),'cargo':subprocess.check_output(['cargo','--version'],text=True).strip(),
        'packageCount':len(packages),'cargoLockPackageCount':len(crates),'venvBytes':size(HERE/'.venv'),'basePythonBytesExcludingSitePackages':size(Path(sys.base_prefix),('site-packages','__pycache__')),
        'executables':{p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in (HERE/'host/target/debug').glob('*.exe')},
        'cargoLockSha256':sha(HERE/'host/Cargo.lock'),'pythonLockSha256':sha(HERE/'requirements.lock'),
        'releasePackageBuilt':False,'cleanWindowsInstallTested':False,'LinuxTested':False,'macOSTested':False,
        'officialSources':['https://v2.tauri.app/start/prerequisites/','https://v2.tauri.app/security/capabilities/','https://v2.tauri.app/distribute/windows-installer/','https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects']}
    try:
        import winreg
        key=winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,r'SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients')
        for i in range(winreg.QueryInfoKey(key)[0]):
            with winreg.OpenKey(key,winreg.EnumKey(key,i)) as c:
                try:
                    if winreg.QueryValueEx(c,'name')[0]=='Microsoft Edge WebView2 Runtime':env['webview2']=winreg.QueryValueEx(c,'pv')[0]
                except OSError:pass
        winreg.CloseKey(key)
    except OSError:pass
    write(HERE/'environment-evidence.json',env)
    regressions={}
    for stage in ('p0-03','p0-04','p0-05'):regressions[stage]=read(HERE.parent/stage/'evidence/latest.json')
    write(HERE/'evidence/regressions.json',regressions)
    baseline=read(HERE/'baseline-manifest.json');changed=[];missing=[]
    for rel,digest in baseline.items():
        p=ROOT/rel
        if not p.exists():missing.append(rel)
        elif sha(p)!=digest:changed.append(rel)
    allowed={'README.md','research/README.md','research/sources.md','research/02-node-contracts/README.md','research/03-execution-engine/README.md','research/05-tool-agent-protocols/README.md','research/08-desktop-runtime/README.md','research/10-feasibility-experiments/README.md',*(f'experiments/{s}/evidence/latest.json' for s in ('p0-03','p0-04','p0-05'))}
    latest=read(HERE/'evidence/latest.json');suite=HERE/latest['directory'];tested=read(suite/'source-hashes.json');drift=[rel for rel,h in tested.items() if sha(ROOT/rel)!=h]
    alive=[];processChecks=[]
    for p in suite.rglob('owned-process-check.json'):
        records=read(p);processChecks+=records;alive+=records and [v for v in records if v['alive']] or []
    assertions=[r for p in suite.rglob('assertions.json') for r in read(p)]
    jobs=[json.loads(line) for p in suite.rglob('host-trace.jsonl') for line in p.read_text().splitlines() if line.strip()]
    badJobs=[x for x in jobs if x['kind']=='owned-job-stopped' and x.get('activeAfterStop')!=0]
    broken=[]
    paths=[HERE/'README.md',*ROOT.glob('planning/p0-06-*.md')]
    for p in paths:
        for target in re.findall(r'\]\(([^)]+)\)',p.read_text(encoding='utf-8')):
            if '://' not in target and not target.startswith('#') and not (p.parent/target.split('#')[0]).exists():broken.append({'file':str(p),'target':target})
    report={'baselineFiles':len(baseline),'changed':changed,'unexpectedChanges':[x for x in changed if x not in allowed],'missing':missing,'testedSourceDrift':drift,
        'ownedPIDChecks':len(processChecks),'ownedStillAlive':alive,'jobStopConfirmations':sum(x['kind']=='owned-job-stopped' for x in jobs),'nonEmptyJobAtStop':badJobs,
        'expectedActualComparisons':len(assertions),'failedComparisons':[r for r in assertions if not r['passed']],'brokenDeliveryLinks':broken,
        'P006':latest['summary'],'regressionCounts':{k:{x:v['summary'][x] for x in ('testsRun','failures','errors')} for k,v in regressions.items()},
        'oldRuntimeSourceChanged':any(x.startswith(('experiments/p0-03/','experiments/p0-04/','experiments/p0-05/')) and not x.endswith('/evidence/latest.json') for x in changed),
        'note':'Checks current final suite; earlier failing suites preserved. Numbers are comparisons/process observations, not extra test passes.'}
    write(HERE/'evidence/delivery-audit.json',report)
    print(json.dumps({k:report[k] for k in ('baselineFiles','unexpectedChanges','missing','testedSourceDrift','ownedPIDChecks','ownedStillAlive','jobStopConfirmations','nonEmptyJobAtStop','expectedActualComparisons','failedComparisons','brokenDeliveryLinks')},ensure_ascii=False))
    return int(any(report[k] for k in ('unexpectedChanges','missing','testedSourceDrift','ownedStillAlive','nonEmptyJobAtStop','failedComparisons','brokenDeliveryLinks')))
if __name__=='__main__':raise SystemExit(main())
