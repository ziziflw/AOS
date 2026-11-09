"""Offline development preview of a pure downstream projection in case A02 only."""
import hashlib
import json
import sqlite3
from copy import deepcopy
from time import perf_counter
from evaluate import HERE, RT, c1, dataset, task_extract, workflow


def preview(source, candidate, stored, binding, adapter_hash):
    # Only this reviewed linear graph, immutable C1 evidence, and a read-only scorer.
    case = next(c for c in dataset['cases'] if c['id']=='A02')
    assert candidate == source == workflow(case,'single'), 'upstream definition or revision changed'
    assert binding == c1.profile.environment(), 'environment changed'
    assert adapter_hash == hashlib.sha256((RT/'local_models.py').read_bytes()).hexdigest(), 'adapter changed'
    assert stored['state']=='succeeded' and not stored['approvals']
    n=stored['nodes']['main/model']
    value=n['outputs']['out']
    assert n['state']=='succeeded' and value['validity']=='validated'
    assert value['contentDigest']==c1.digest(value['payload'])
    assert value['provenance']['attemptId']==n['attempts'][-1]['id']
    assert value['provenance']['workflowRevision']==source['version']['revision']
    tasks=task_extract.checked(value['payload'])['tasks']
    return sorted(t['owner'] for t in tasks)


if __name__=='__main__':
    if not __debug__:
        raise SystemExit('Use normal Python mode to retain evaluation assertions')
    report=json.loads((HERE/'pinSource.json').read_text('utf-8'))
    from pathlib import Path
    d=Path(report['workspace']).resolve()/'A02-single-0'
    assert d.is_relative_to(RT/'evidence') and d.parent.name.startswith('p010-')
    source=c1.read(d/'workflow.json')
    binding=c1.read(d/'environment.json')
    with sqlite3.connect((d/'run.sqlite').as_uri()+'?mode=ro',uri=True) as db:
        raw,checksum=db.execute('select state,checksum from snapshot where id=1').fetchone()
    state=json.loads(raw)
    assert c1.digest(state)==checksum
    start=perf_counter()
    args=[source,source,state,binding,report['adapterSHA']]
    owners=preview(*args)
    duration=(perf_counter()-start)*1000
    assert owners==['李四','王五']
    rejected=[]
    for field in ['text','model','revision','binding','adapter']:
        modified=deepcopy(args)
        candidate=deepcopy(source)
        modified[1]=candidate
        if field=='text': candidate['graph']['nodes'][0]['config']['value']+='改'
        if field=='model': candidate['graph']['nodes'][1]['config']['maxOutputTokens']+=1
        if field=='revision': candidate['version']['revision']='other'
        if field=='binding': modified[3]['extensions']['aos:local-connections']={}
        if field=='adapter': modified[4]='changed'
        try:preview(*modified)
        except AssertionError:rejected.append(field)
    assert len(rejected)==5
    print(json.dumps(dict(sourceRun=state['runId'],workflowRevision=state['workflowRevision'],
                          attempt=state['nodes']['main/model']['attempts'][0]['id'],
                          projection='sort owners after existing JSON check',owners=owners,
                          rejected=rejected,previewMs=duration),ensure_ascii=False))

