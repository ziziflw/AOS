"""Read-only history, test/source, process, secret-log and link audit."""
import hashlib,json,re
from pathlib import Path
from bootstrap_agent import HERE,ROOT,P03,P04,SECRET,read,write
def main():
    allowed={'README.md','research/README.md','research/sources.md','planning/p0-05-architecture-findings.md','experiments/p0-03/runtime.py',
       'experiments/p0-03/evidence/latest.json','experiments/p0-04/evidence/latest.json',*[f'research/{name}/README.md' for name in
       ('02-node-contracts','03-execution-engine','05-tool-agent-protocols','07-security-permissions','08-desktop-runtime','10-feasibility-experiments')]}
    baseline=read(HERE/'baseline-manifest.json');changed=[];missing=[]
    for name,sha in baseline.items():
        p=ROOT/name
        if not p.exists():missing.append(name)
        elif hashlib.sha256(p.read_bytes()).hexdigest()!=sha:changed.append(name)
    latest=read(HERE/'evidence/latest.json');suite=HERE/latest['directory'];hashes=read(suite/'source-hashes.json')
    drift=[name for name,sha in hashes.items() if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=sha]
    reg={stage:read(path/'evidence/latest.json') for stage,path in [('p0-03',P03),('p0-04',P04)]}
    write(HERE/'evidence/regressions.json',reg)
    process_rows=[r for p in suite.glob('test_*/process-cleanup.json') for r in read(p)]
    checks=[r for p in suite.glob('test_*/assertions.json') for r in read(p)]
    leaks=[]
    for p in suite.rglob('*'):
        if p.is_file() and p.suffix in ('.json','.jsonl','.log') and SECRET in p.read_text(encoding='utf-8',errors='replace'):leaks.append(p.relative_to(HERE).as_posix())
    broken=[];audit=(HERE/'evidence/delivery-audit.json').resolve()
    docs=[ROOT/n for n in allowed if n.endswith('.md')]+[HERE/'README.md',*sorted((ROOT/'planning').glob('p0-05-*.md'))]
    for p in set(docs):
        if not p.exists():broken.append(str(p));continue
        for target in re.findall(r'\]\(([^)]+)\)',p.read_text(encoding='utf-8')):
            if '://' in target or target.startswith('#'):continue
            q=(p.parent/target.split('#',1)[0]).resolve()
            if q!=audit and not q.exists():broken.append({'file':p.relative_to(ROOT).as_posix(),'target':target})
    def compact(s):return {k:s[k] for k in ('testsRun','failures','errors')}
    result={'classification':'delivery audit, separate from execution method counts','baselineFiles':len(baseline),'changedExisting':changed,'missingExisting':missing,
       'unexpectedChanges':sorted(set(changed)-allowed),'testedSourceDrift':drift,'brokenLocalLinks':broken,'secretMarkerLeaks':leaks,
       'processChecks':len(process_rows),'ownedProcessAlive':[r for r in process_rows if r['alive']],'AgentTests':compact(latest['summary']),
       'regressions':{stage:compact(record['summary']) for stage,record in reg.items()},'assertionComparisons':len(checks),'allComparisonsPassed':all(r['passed'] for r in checks),
       'wheelHashesMatchInstallReport':read(HERE/'environment-evidence.json')['wheelHashesMatchInstallReport']}
    counts=[result['AgentTests'],*result['regressions'].values()]
    result['passed']=not any(result[k] for k in ('missingExisting','unexpectedChanges','testedSourceDrift','brokenLocalLinks','secretMarkerLeaks','ownedProcessAlive')) and result['allComparisonsPassed'] and result['wheelHashesMatchInstallReport'] and [c['testsRun'] for c in counts]==[18,18,14] and all(c['failures']==c['errors']==0 for c in counts)
    write(audit,result);print(json.dumps(result,ensure_ascii=False,indent=2));return 0 if result['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
