"""Run fixed P0-10 cases against the installed C1 Session and loopback Gemma."""
import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path
import sys
import time
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
RT = Path(os.environ['LOCALAPPDATA']) / 'AOS-Demo/v0.1.3/experiments/p0-08'
sys.path.insert(0, str(RT))
import executor as c1
import httpx2
import openai
import task_extract

dataset = json.loads((HERE / 'cases.json').read_text('utf-8-sig'))
MODEL = 'google/gemma-4-e4b'
URL = 'http://127.0.0.1:1234/v1'
LOCAL = 'p08.lmstudio.text'
profile = c1.profile


def elapsed(start):
    return round((time.perf_counter() - start) * 1000, 2)


def prompt(case):
    if case['rule'] == 'tasks':
        return case['input'] + '\n\n' + dataset['instruction']
    return case['input']


def parameters(case):
    return dict(model=MODEL, messages=[dict(role='user', content=prompt(case))],
                max_tokens=case.get('maxTokens', 192), stream=False, reasoning_effort='none')


def score_text(case, raw):
    if case['rule'] == 'tasks':
        tasks = task_extract.checked(raw)['tasks']
        found = [[t['task'], t['owner'], t['due']] for t in tasks]
        return sorted(found, key=str) == sorted(case['expected'], key=str)
    return raw.strip() == case['expected']


def workflow(case, route):
    tids = list(case['nodes'])
    if case['id'].startswith('C') and route == 'single':
        tids = ['synth.source', LOCAL, 'synth.output']
    w = profile.sample(LOCAL)['workflow']
    names = {'synth.source':'text', 'synth.output':'output', 'aos.validate-tasks':'validate',
             'p07.echo-args':'args', 'tool.mcp.echo_text':'tool', 'p07.echo-text':'unpack'}
    nodes = [profile.make_node(t, names.get(t,'model')) for t in tids]
    nodes[0]['config']['value'] = prompt(case)
    for n in nodes:
        if n['typeId'] == LOCAL:
            n['config'].update(maxOutputTokens=case.get('maxTokens',192), maxInputTokens=2048, maxCallCostMinor=30)
        if case['rule'] == 'cancel' and n['id'] == 'model':
            n['policy']['approval'] = 'always'
        if n['typeId'] == 'p08.openai.text':
            n['config']['model'] = 'fixture-lost'
    edges = [profile.edge(a['id'], b['id'], inp='args' if b['id']=='tool' else 'in', index=i)
             for i,(a,b) in enumerate(zip(nodes,nodes[1:]))]
    w.update(graph={'nodes':nodes,'edges':edges}, environmentRequirements=profile.requirements(nodes),
             workflowId='eval-'+case['id'].lower(), version={'revision':'p010-v1'})
    return w


async def close_session(x):
    await x.runtime.close()
    await x.registry.close()
    x.release_resources()
    x.store.close()
    x.system.close()


async def measure(case, route, directory):
    row = dict(id=case['id'], route=route, requests=[], passed=False, reason=None)
    original = httpx2.AsyncClient.send

    async def observed(client, request, **kw):
        if request.url.host != '127.0.0.1':
            raise AssertionError('non-loopback HTTP')
        start = time.perf_counter()
        event = dict(method=request.method, path=request.url.path, localGemma=request.url.port==1234)
        row['requests'].append(event)
        response = await original(client, request, **kw)
        event.update(ms=elapsed(start), http=response.status_code)
        if event['localGemma'] and request.method=='POST':
            body = response.json()
            usage = body.get('usage') or {}
            event.update(body=json.loads(request.content), usage=usage, cachedTokens=(usage.get('prompt_tokens_details') or {}).get('cached_tokens'),
                         finish=body['choices'][0]['finish_reason'], text=body['choices'][0]['message']['content'])
        return response

    start = time.perf_counter()
    x = None
    try:
        with patch.object(httpx2.AsyncClient,'send',observed):
            if route == 'direct':
                async with openai.AsyncOpenAI(base_url=URL,api_key='local-no-auth',max_retries=0,timeout=20,
                         http_client=httpx2.AsyncClient(trust_env=False,follow_redirects=False)) as client:
                    result = await client.chat.completions.create(**parameters(case),extra_headers={'Authorization':openai.omit})
                row['totalMs'] = elapsed(start)
                choice = result.choices[0]
                row['passed'] = (choice.finish_reason=='length' if case['rule']=='cutoff'
                                 else score_text(case, choice.message.content))
            else:
                w = workflow(case,route)
                row['workflowSha256'] = c1.digest(w)
                x = c1.Session(directory,w)
                s = await x.runtime.drive()
                if case['rule']=='cancel':
                    assert s['state']=='waiting-approval', 'missing approval gate'
                    x.runtime.cancel()
                    s = await x.runtime.drive()
                if case['rule']=='recover':
                    assert s['state']=='unknown' and len(x.fixture.rows)==1, 'lost response not quarantined'
                    previous = s['runId']
                    await close_session(x)
                    x = None
                    x = c1.Session(directory,w,recover=True)
                    s = await x.runtime.drive()
                    assert previous==s['runId'] and not x.fixture.rows, 'unexpected replay'
                row['totalMs'] = elapsed(start)
                assert s==x.store.load(), 'SQLite and runtime disagree'
                row.update(runId=s['runId'], state=s['state'], result=s['scopes']['main'].get('result'),
                           nodes={k:{'state':n['state'],'attempts':len(n['attempts']),'error':(n.get('error') or {}).get('code')}
                                  for k,n in s['nodes'].items()})
                output = s['nodes']['main/output']
                codes = [n['error'] for n in row['nodes'].values() if n['error']]
                rule = case['rule']
                if rule in ('invalid-tool','cutoff') or (rule=='validate' and case['expected']):
                    row['passed'] = s['state']=='failed' and case['expected'] in codes and not output['attempts']
                    if rule=='invalid-tool':
                        assert not s['nodes']['main/tool']['attempts']
                elif rule in ('recover','cancel'):
                    row['passed'] = s['state']==case['expected'] and not output['attempts']
                elif rule=='validate':
                    row['passed'] = s['state']=='succeeded' and json.loads(row['result'])==json.loads(case['input'])
                else:
                    row['passed'] = s['state']=='succeeded' and score_text(case,row['result'])
                    if route=='tool' and s['state']=='succeeded':
                        nodes=s['nodes']
                        model_text=nodes['main/model']['outputs']['out']['payload']
                        assert nodes['main/tool']['attempts'][0]['inputs']['args']=={'text':model_text}
                        assert row['result']==model_text and len(nodes['main/tool']['attempts'])==1
            generations=[r for r in row['requests'] if r['localGemma'] and r['method']=='POST']
            assert len(generations)==int(case['realGemma']), 'unexpected generation count'
            assert all(r['body']==parameters(case) for r in generations), 'request parameters or context changed'
            if not row['passed']:
                row['reason']='expected '+json.dumps(case['expected'],ensure_ascii=False)+'; inspect recorded response and C1 status'
    except Exception as exc:
        row['reason']=f'{type(exc).__name__}: {exc}'
        row['passed']=False
    finally:
        if x:
            await close_session(x)
    return row


async def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('label')
    parser.add_argument('ids',nargs='*')
    args=parser.parse_args()
    if not args.label.isascii() or not args.label.isalnum():
        parser.error('use an alphanumeric label')
    from local_models import read
    assert read().get('LM Studio')=={'model':MODEL,'url':URL}, 'check LM Studio connection first'
    results=HERE/(args.label+'.json')
    if results.exists():
        raise FileExistsError('Use a fresh label to retain previous evidence')
    root=RT/'evidence'/('p010-'+str(time.time_ns()))
    info=dict(datasetSHA=hashlib.sha256((HERE/'cases.json').read_bytes()).hexdigest(),
              adapterSHA=hashlib.sha256((RT/'local_models.py').read_bytes()).hexdigest(),
              model=MODEL, workspace=str(root), rows=[])
    with httpx2.Client(trust_env=False,timeout=5) as client:
        metadata=client.get('http://127.0.0.1:1234/api/v1/models').json()['models']
        info['modelMetadata']=next(m for m in metadata if m['key']==MODEL)
    for c in dataset['cases']:
        if args.ids and c['id'] not in args.ids:
            continue
        routes=['direct','single'] if c['realGemma'] else ['single']
        if c['id'].startswith('C'):
            routes.append('tool')
        for repeat in range(2 if c['id'] in ('A02','D03') else 1):
            for route in routes:
                row=await measure(c,route,root/f"{c['id']}-{route}-{repeat}")
                info['rows'].append(dict(row,repeat=repeat))
                results.write_text(json.dumps(info,ensure_ascii=False,indent=2),'utf-8')
                print(c['id'],route,row['passed'],row['reason'] or '',flush=True)
    return all(r['passed'] for r in info['rows'])

if __name__=='__main__':
    sys.exit(0 if asyncio.run(main()) else 1)

