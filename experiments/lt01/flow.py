"""LT01 profile atop the installed C1 scheduler, model guard, contracts and store."""
import argparse, asyncio, csv, hashlib, json, os, re, sys, time
from pathlib import Path
from copy import deepcopy
from unittest.mock import patch
from contextlib import AsyncExitStack
import audit

ROOT=Path(__file__).resolve().parent
RT=Path(os.environ['LOCALAPPDATA'])/'AOS-Demo/v0.1.3/experiments/p0-08'
sys.path.insert(0,str(RT))
import executor as c1
from fixtures import node,edge,port,obj,policy
from mocks import Result,MockRegistry
from common import ContractError,OutcomeError,read,write
from mcp import ClientSession,StdioServerParameters
from mcp.client.stdio import stdio_client
import httpx2
MODEL='p08.lmstudio.text'
ID='google/gemma-4-e4b'
F='FileReference'; V='Validation'; T='Text'
STAGES={'read':([],F),'parse':([('in',F)],F),'normalize':([('in',F)],F),'join':([('in',F)],F),
        'decision':([('in',F)],V),'prompt':([('in',V)],T),'empty':([('in',V)],T),
        'check':([('in',T),('facts',F)],T),'review':([('in',T)],T)}
def typed(name,direction,kind):
    return port(name,direction,kind if kind in (T,F) else 'JSON',ref=kind if kind==V else None)

def prepare():
    catalog=read(c1.profile.CATALOG)
    existing={d['typeId'] for d in catalog['nodeDefinitions']}
    controls_catalog=read(ROOT.parent/'p0-03/fixtures/catalog.json')
    catalog['nodeDefinitions'].extend(d for d in controls_catalog['nodeDefinitions']
        if d['typeId'] in ('core.condition','synth.merge-exclusive') and d['typeId'] not in existing)
    controls=catalog['nodeDefinitions'][0]['ports'][-3:]
    for name,(inputs,output) in STAGES.items():
        catalog['nodeDefinitions'].append(dict(typeId='lt.'+name,version='0.1.0',executionKind='builtin',
            ports=[typed(k,'input',t) for k,t in inputs]+[typed('out','output',output)]+deepcopy(controls),
            configSchema=obj({}),effect='read' if name=='read' else 'none',supportedControls=list(policy())))
    cat=ROOT/'catalog.json';write(cat,catalog)
    nodes=[node(k,'lt.'+k) for k in STAGES]
    nodes.extend([node('branch','core.condition',{'pointer':'/valid','equals':True}),
                  c1.profile.make_node(MODEL,'model'),node('merge','synth.merge-exclusive',{'mode':'exactly-one-active'}),
                  node('output','synth.output')])
    for n in nodes:
        if n['id']=='review':n['policy']['approval']='always'
        if n['id']=='model':n['config'].update(maxInputTokens=2048,maxOutputTokens=384,maxCallCostMinor=30)
    links=[edge(a,b,index=i) for i,(a,b) in enumerate(zip(('read','parse','normalize','join','decision'),
                                                                  ('parse','normalize','join','decision','branch')))]
    for a,b,o,k,order in [('branch','prompt','pass','in',0),('branch','empty','fail','in',0),('prompt','model','out','in',0),
        ('model','check','out','in',0),('join','check','out','facts',0),('check','review','out','in',0),
        ('review','merge','out','items',0),('empty','merge','out','items',1),('merge','output','out','in',0)]:
        links.append(edge(a,b,out=o,inp=k,index=len(links),order=order))
    w=c1.profile.sample(MODEL)['workflow']
    w.update(workflowId='lt01-audit',title='模拟电商综合审计',graph={'nodes':nodes,'edges':links},environmentRequirements=c1.profile.requirements(nodes))
    w['catalogLock']['sha256']=hashlib.sha256(cat.read_bytes()).hexdigest()
    w['executionPolicy'].update(concurrencyLimit=1,timeoutMs=1800000)
    write(ROOT/'workflow.json',w)

def blob(directory,data):
    raw=json.dumps(data,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
    h=hashlib.sha256(raw).hexdigest();p=directory/(h+'.json')
    if not p.exists():p.write_bytes(raw)
    return dict(resourceUri='artifact:'+h,sha256=h,sizeBytes=len(raw),mediaType='application/json')

def fetch(directory,ref):
    h=ref['sha256']
    if not re.fullmatch('[a-f0-9]{64}',h) or ref['resourceUri']!='artifact:'+h:raise ValueError('BAD_REFERENCE')
    data=(directory/(h+'.json')).read_bytes()
    if hashlib.sha256(data).hexdigest()!=h or len(data)!=ref['sizeBytes']:raise ValueError('ARTIFACT_DRIFT')
    return json.loads(data)

class Registry(c1.Registry):
    def metadata(self,t):
        if t.startswith('lt.') and t[3:] in STAGES:return {'effect':'read' if t=='lt.read' else 'none'}
        if t in ('core.condition','synth.merge-exclusive'):return MockRegistry.metadata(self,t)
        return super().metadata(t)

    async def invoke(self,ctx):
        t=ctx.node['typeId']; x=ctx.inputs; data=self.dir/'blobs'
        if t in ('core.condition','synth.merge-exclusive'):return await MockRegistry.invoke(self,ctx)
        if not t.startswith('lt.'):return await super().invoke(ctx)
        step=t[3:]
        if step=='read':
            launch=StdioServerParameters(command=sys.executable,args=['-B','-X','utf8',str(ROOT/'reader.py')],
                     env={'LT01_FAULT':self.plan['fault'],'PYTHONDONTWRITEBYTECODE':'1'})
            try:
                async with AsyncExitStack() as stack:
                    io=await stack.enter_async_context(stdio_client(launch))
                    client=await stack.enter_async_context(ClientSession(*io))
                    await client.initialize()
                    names=[t.name for t in (await client.list_tools()).tools]
                    if names!=['read_dataset']: raise ValueError('MCP_TOOL_DRIFT')
                    r=await client.call_tool('read_dataset',{'size':self.plan['size']})
                    if r.isError:raise ValueError('MCP_READ_ERROR')
                    raw=r.structuredContent or json.loads(r.content[0].text)
                    write(self.dir/'mcp.json',dict(tool=names[0],files=list(raw),attempt=ctx.attempt_id))
            except Exception as e:raise OutcomeError('MCP_READ_FAILED') from e
            result=blob(data,raw)
        elif step in ('parse','normalize','join'):
            if step=='join' and self.plan['fault']=='crash':os._exit(74)
            fn={'parse':audit.parse,'normalize':audit.normalize,'join':audit.reconcile}[step]
            result=blob(data,fn(fetch(data,x['in'])))
            if step=='normalize' and self.plan['fault']=='bad-port':result=12
        elif step=='decision':
            ref=x['in'];tickets=fetch(data,ref)['tickets']
            result=dict(valid=bool(tickets),issues=[v['ticket'] for v in tickets],result=dict(artifact=ref,operationId=ctx.operation_id,effectState='confirmed'))
        elif step=='prompt':result=audit.prompt(fetch(data,x['in']['result']['artifact'])['tickets'])
        elif step=='empty':result=json.dumps(dict(facts=x['in']['result']['artifact'],advice=[]))
        elif step=='check':
            answers=audit.adjudicate(x['in'],fetch(data,x['facts'])['tickets'])
            result=json.dumps(dict(facts=x['facts'],advice=answers),ensure_ascii=False)
        else:result=x['in']
        return Result({'out':result})

def export(directory,state):
    result=json.loads(state['scopes']['main']['result'])
    facts=fetch(directory/'blobs',result['facts'])
    target=directory/'results';target.mkdir(exist_ok=True)
    with (target/'reconciliation.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=['order','amount','paid','refund','shipments']);w.writeheader();w.writerows(facts['rows'])
    write(target/'exceptions.json',facts['issues'])
    write(target/'action-plan.json',result['advice'])
    (target/'audit-report.md').write_text('# 模拟订单审计\n\n'+f"{len(facts['rows'])} 笔订单，{len(facts['issues'])} 项待核实记录。金额单位为分。\n\n"+
        '\n'.join(f"- {v['ticket']} · {v['category']} · {v['action']}" for v in result['advice']),'utf-8')

async def main(a):
    if not re.fullmatch('[a-zA-Z0-9_-]{1,48}',a.label):raise ValueError('LABEL')
    directory=ROOT/'runs'/a.label
    directory.mkdir(parents=True,exist_ok=a.resume)
    (directory/'blobs').mkdir(exist_ok=True)
    w=read(ROOT/'workflow.json');w['executionPolicy']['timeoutMs']=a.minutes*60000
    binding=c1.profile.environment()
    binding['extensions']['aos:local-connections']={'LM Studio':{'model':ID,'url':'http://127.0.0.1:1234/v1'}}
    system=c1.SyntheticSystem(directory/'synthetic.sqlite')
    reg=Registry(system,directory,binding)
    reg.plan={'size':a.size,'fault':a.fault,'inputs':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'inputs'/a.size).iterdir()},
              'build':{f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in ['flow.py','audit.py','reader.py']}}
    c=c1.Contracts(w,c1.profile.request(w),ROOT/'catalog.json',c1.SchemaAdapter(c1.ROOT/'research/02-node-contracts/schemas/contract.schema.json',ROOT/'catalog.json'),reg)
    store=c1.GuardedStore(directory/'run.sqlite')
    rt=c1.ModelRuntime(c,store,reg,binding,approval_ttl=a.minutes*60);reg.runtime=rt
    original=httpx2.AsyncClient.send
    async def traced(client,req,**kwargs):
        if req.url.host!='127.0.0.1' or req.url.port!=1234:raise ValueError('LOOPBACK_ONLY')
        log=directory/'requests.jsonl'
        def record(event):
            with log.open('a',encoding='utf-8') as f:f.write(json.dumps(event,ensure_ascii=False)+'\n')
        start=time.perf_counter()
        if req.method=='POST':
            if log.exists() and any(json.loads(l)['kind']=='generate' for l in log.read_text('utf-8').splitlines()):raise ValueError('CALL_CAP')
            record(dict(kind='generate',body=json.loads(req.content)))
            if a.fault=='timeout':
                raise httpx2.ReadTimeout('LT01 injected read timeout',request=req)
        response=await original(client,req,**kwargs)
        if req.method=='POST':
            body=response.json()
            record(dict(kind='received',usage=body.get('usage'),text=body['choices'][0]['message']['content'],ms=1000*(time.perf_counter()-start)))
            if a.fault=='lost':raise httpx2.ReadError('LT01 response lost after local operation',request=req)
        return response
    try:
        if a.approve:
            pending=rt.snapshot['approvals'].get(a.approve)
            if not pending:raise ValueError('WRONG_APPROVAL_ID')
            rt.approve(a.approve,pending['fingerprint'],True)
        with patch.object(httpx2.AsyncClient,'send',traced):
            s=await rt.drive()
        if s!=store.load():raise RuntimeError('STATE_DIVERGENCE')
        write(directory/'snapshot.json',s);write(directory/'events.json',store.events())
        if s['state']=='succeeded':export(directory,s)
        metrics=dict(runId=s['runId'],state=s['state'],usage=s['usage'],wallSeconds=time.time()-s['createdAt'],
                     attempts={k:len(v['attempts']) for k,v in s['nodes'].items()},pending=[k for k,v in s['approvals'].items() if v['status']=='pending'])
        write(directory/'execution-metrics.json',metrics)
        if s['state']=='succeeded':write(directory/'results/execution-metrics.json',metrics)
        print(json.dumps(metrics,ensure_ascii=False))
        print([(k,n.get('error')) for k,n in s['nodes'].items() if n.get('error')])
        if metrics['pending']:print(rt._dependencies('main/review')[1]['in'])
    finally:
        await rt.close();await reg.close();store.close();system.close()

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('label');p.add_argument('--size',choices=['30','200'],default='30')
    p.add_argument('--fault',choices=['none','mcp-stop','bad-port','crash','timeout','lost'],default='none')
    p.add_argument('--resume',action='store_true');p.add_argument('--approve');p.add_argument('--minutes',type=int,default=30)
    a=p.parse_args()
    if a.label=='prepare':prepare()
    else:asyncio.run(main(a))

