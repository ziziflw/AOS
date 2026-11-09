"""Delivery audit is separate from MCP tests and P0-03 regression counts."""
import hashlib,json,re
from pathlib import Path
from bootstrap import HERE,ROOT,P03,read,write
def main():
    allowed={'README.md','research/README.md','research/sources.md',*[f'research/{x}/README.md' for x in
        ('02-node-contracts','03-execution-engine','05-tool-agent-protocols','08-desktop-runtime','10-feasibility-experiments')],
        'experiments/p0-03/common.py','experiments/p0-03/contracts.py','experiments/p0-03/evidence/latest.json'}
    baseline=read(HERE/'baseline-manifest.json'); changed=[]; missing=[]
    for name,sha in baseline.items():
        p=ROOT/name
        if not p.exists(): missing.append(name)
        elif hashlib.sha256(p.read_bytes()).hexdigest()!=sha: changed.append(name)
    latest=read(HERE/'evidence/latest.json'); suite=HERE/latest['directory']
    hashes=read(suite/'source-hashes.json')
    drift=[name for name,sha in hashes.items() if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=sha]
    regression=read(P03/'evidence/latest.json');write(HERE/'evidence/p0-03-regression.json',regression)
    snapshots=[read(p) for p in suite.glob('test_*/process-cleanup.json')]
    broken=[]; target_audit=HERE/'evidence/delivery-audit.json'
    docs=[ROOT/x for x in allowed if x.endswith('.md')]+[HERE/'README.md',*sorted((ROOT/'planning').glob('p0-04-*.md'))]
    for p in docs:
        if not p.exists(): broken.append(str(p));continue
        for target in re.findall(r'\]\(([^)]+)\)',p.read_text(encoding='utf-8')):
            if '://' in target or target.startswith('#'): continue
            q=(p.parent/target.split('#')[0]).resolve()
            if q!=target_audit and not q.exists(): broken.append({'document':p.relative_to(ROOT).as_posix(),'target':target})
    env=read(HERE/'environment-evidence.json')
    current=latest['summary']; old=regression['summary']
    assertions=[r for p in suite.glob('test_*/assertions.json') for r in read(p)]
    result={'classification':'delivery audit; not an additional execution test','baselineCount':len(baseline),'changedExisting':changed,
        'missingExisting':missing,'unexpectedChanges':sorted(set(changed)-allowed),'testedSourceDrift':drift,'brokenLocalLinks':broken,
        'ownedProcessChecks':sum(map(len,snapshots)),'ownedProcessAlive':[x for rows in snapshots for x in rows if x['alive']],
        'MCPTests':{'testsRun':current['testsRun'],'failures':current['failures'],'errors':current['errors']},
        'P03Regression':{'testsRun':old['testsRun'],'failures':old['failures'],'errors':old['errors']},
        'wheelHashesMatchInstallReport':env['wheelHashesMatchInstallReport'],'assertionComparisons':len(assertions),'allComparisonsPassed':all(x['passed'] for x in assertions)}
    result['passed']=not any(result[k] for k in ('missingExisting','unexpectedChanges','testedSourceDrift','brokenLocalLinks','ownedProcessAlive')) and result['allComparisonsPassed'] and result['wheelHashesMatchInstallReport'] and current['testsRun']==14 and old['testsRun']==18 and current['failures']==current['errors']==old['failures']==old['errors']==0
    write(target_audit,result);print(json.dumps(result,ensure_ascii=False,indent=2));return 0 if result['passed'] else 1
if __name__=='__main__': raise SystemExit(main())
