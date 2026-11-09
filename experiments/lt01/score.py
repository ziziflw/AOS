"""Independent fixture evaluator. Never imported by the workflow."""
from pathlib import Path
import argparse
import csv
import hashlib
import json
import re
import sqlite3
from collections import Counter

ROOT=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_text('utf-8'))
def authoritative(d):
    with sqlite3.connect((d/'run.sqlite').resolve().as_uri()+'?mode=ro',uri=True) as db:
        state,=db.execute('select state from snapshot where id=1').fetchone()
    return json.loads(state)
def records(d):
    f=d/'requests.jsonl'
    return [json.loads(l) for l in f.read_text('utf-8').splitlines()] if f.exists() else []

def refs(oid,flag):
    i=int(oid[1:]);o=f'Orow{i}';p=f'P{i}';s=f'S{i}-0';r=f'R{i}'
    return {'duplicate_order':[o],'amount_mismatch':[o,p],'missing_payment':[o],'over_refund':[o,p,r],
       'duplicate_refund':[r],'unshipped':[o,p],'multiple_shipments':[o,s,f'S{i}-1'],
       'complaint':[o,f'T{i}',s],'invalid_payment':[f'X{i}']}[flag]

def grade(label,size):
    if not re.fullmatch('[A-Za-z0-9_-]{1,48}',label):raise ValueError('LABEL')
    d=ROOT/'runs'/label;target=d/'results';truth=read(ROOT/'oracle'/f'{size}.json')
    state=authoritative(d);paused=read(d/'paused.json');metrics=read(target/'execution-metrics.json')
    grades={};blocks=[]
    with (target/'reconciliation.csv').open(encoding='utf-8',newline='') as f:rows=list(csv.DictReader(f))
    recon={r['order']:{k:int(r[k]) for k in ['paid','amount','refund','shipments']} for r in rows}
    valid=len(rows)==len(truth)==len(recon) and all(all(truth[o][k]==v for k,v in values.items()) for o,values in recon.items())
    grades['ledger']=35*valid
    actual=read(target/'exceptions.json')
    flags=Counter((k,t) for k,v in truth.items() for t in v['flags'])
    found=Counter((v['order'],v['kind']) for v in actual)
    grades['flags']=10*(flags==found)
    grades['records']=10*(found==flags and all(sorted(refs(v['order'],v['kind']))==sorted(v['evidence']) and v['detail'] for v in actual))
    advice=read(target/'action-plan.json')
    expected={'T'+str(int(o[1:])):v['review'] for o,v in truth.items() if v['review']}
    grades['semantic']=5*(len(advice)==len(expected) and all(expected[v['ticket']]==v['category'] and v['priority']==('high' if v['category']=='conflict' else 'normal') for v in advice))
    events=read(d/'events.json')
    approvals=[e['seq'] for e in events if e['kind']=='approval-resolved' and e.get('decision') is True]
    dispatch=[e['seq'] for e in events if e['kind']=='node-dispatched' and e['key']=='main/review']
    if len(approvals)!=1 or len(dispatch)!=1 or approvals[0]>=dispatch[0] or state['nodes']['main/review']['state']!='succeeded':blocks.append('approval provenance')
    final=json.loads(state['scopes']['main']['result'])
    ref=final['facts'];data=(d/'blobs'/(ref['sha256']+'.json')).read_bytes()
    facts=json.loads(data)
    same=(state==read(d/'snapshot.json') and state['state']==metrics['state']=='succeeded' and state['runId']==metrics['runId']
          and hashlib.sha256(data).hexdigest()==ref['sha256'] and final['advice']==advice and facts['issues']==actual
          and facts['rows']==[{'order':r['order'],**recon[r['order']]} for r in rows])
    if not same:blocks.append('artifact / SQLite divergence')
    preserved=all(n['attempts']==state['nodes'][k]['attempts'] for k,n in paused['nodes'].items() if n['state']=='succeeded')
    grades['restore']=6*(paused['state']=='waiting-approval' and paused['runId']==state['runId'] and preserved and any(e['kind']=='recovered' for e in events))
    grades['gate']=4*(not blocks)
    challenges=ROOT/'challenges.json'
    results=read(challenges) if challenges.exists() else {}
    for mode in ['timeout','mcp-stop','bad-port','crash','lost']:
        grades[mode]=2*bool(results.get(mode,{}).get('verified'))
        if results.get(mode,{}).get('unsafe'):blocks.append(mode)
    wire=records(d);calls=[e for e in wire if e['kind']=='generate'];responses=[e for e in wire if e['kind']=='received']
    if len(calls)>1:blocks.append('duplicate generation')
    usage=responses[0]['usage'] if responses else {}
    grades['efficiency']=10*(len(calls)==len(responses)==1 and state['usage']['spentTokens']==usage.get('total_tokens') and state['usage']['spentTokens']<=4096
                             and len(calls[0]['body']['messages'])==1 and all(k in calls[0]['body']['messages'][0]['content'] for k in expected) and 'Orow' not in calls[0]['body']['messages'][0]['content'])
    grades['deliverables']=10*(same and all((target/name).stat().st_size>0 for name in ['reconciliation.csv','exceptions.json','action-plan.json','audit-report.md','execution-metrics.json']) and str(size) in (target/'audit-report.md').read_text('utf-8'))
    report=dict(points=sum(grades.values()),grades=grades,blockers=blocks,passed=not blocks and sum(grades.values())==100,
                note='Scope: CLI execution profile; GUI diagnostics separately unverified')
    (d/'score.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf-8');print(label,report)
    return report
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('label');p.add_argument('size',choices=['30','200']);a=p.parse_args()
    grade(a.label,a.size)

