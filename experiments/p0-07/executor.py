"""P0-07 draft API layered on P0-06 transport and original C1. No second scheduler."""
import argparse,asyncio,hashlib,os,re,sys,time,uuid
from copy import deepcopy
from types import SimpleNamespace
from pathlib import Path
from boot import HERE,ROOT,read,write,digest,ContractError,OutcomeError
import importlib.util
spec=importlib.util.spec_from_file_location('p006_endpoint',HERE.parent/'p0-06/executor.py')
p006=importlib.util.module_from_spec(spec);spec.loader.exec_module(p006)
from workbench_profile import CATALOG,LABELS,DEFAULTS,environment,request,requirements,sample
from contracts import Contracts
from schema_adapter import SchemaAdapter
from integration import MCPRegistry,BoundRuntime,GuardedStore
from mocks import SyntheticSystem,Result
import windows_adapter,mcp_client
# Reuse the reviewed Windows process adapter with this experiment's fixed root.
windows_adapter.HERE=HERE
mcp_client.ProcessHost=windows_adapter.LocalMCPHost

def profile_digest():
    files=[HERE/'executor.py',HERE/'workbench_profile.py',HERE/'windows_adapter.py',HERE/'mcp_server_entry.py',CATALOG,
           HERE.parent/'p0-03/runtime.py',HERE.parent/'p0-03/contracts.py',HERE.parent/'p0-04/integration.py',HERE.parent/'p0-04/mcp_client.py']
    return digest({str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files})

class Registry(MCPRegistry):
    def metadata(self,tid):
        if tid.startswith('p07.') and tid in LABELS:return {'effect':'none'}
        if tid not in LABELS:raise ContractError('IMPLEMENTATION_UNAVAILABLE')
        return super().metadata(tid)
    async def invoke(self,ctx):
        t=ctx.node['typeId'];x=ctx.inputs;c=ctx.node['config']
        if not t.startswith('p07.'):return await super().invoke(ctx)
        self.system.begin(ctx)
        if t=='p07.model':
            # Deterministic local synthetic text; temperature is validated, not claimed as real inference.
            try:await asyncio.wait_for(ctx.cancel.wait(),c['delayMs']/1000)
            except asyncio.TimeoutError:pass
            if ctx.cancel.is_set():raise asyncio.CancelledError()
            if c['fail']:raise OutcomeError('P07_SYNTHETIC_MODEL_FAILURE')
            v=('合成回答：'+x['in'])[:c['maxOutputTokens']]
        elif t=='p07.echo-args':v={'text':x['in']}
        elif t=='p07.effect-args':v={'value':x['in']}
        elif t=='p07.echo-text':v=x['in']['text']
        elif t=='p07.effect-text':v=x['in']['value']
        else:raise ContractError('IMPLEMENTATION_UNAVAILABLE')
        self.system.finish(ctx);return Result({'out':v})

class Session:
    def __init__(self,directory,w,*,recover=False):
        self.dir=directory;directory.mkdir(exist_ok=True,parents=True)
        self.v=SchemaAdapter(ROOT/'research/02-node-contracts/schemas/contract.schema.json',CATALOG)
        if not recover:
            for name,value in [('workflow',w),('request',request(w)),('environment',environment())]:write(directory/(name+'.json'),value)
        w,r,e=(read(directory/(name+'.json')) for name in ('workflow','request','environment'))
        self.system=SyntheticSystem(directory/'synthetic.sqlite')
        self.registry=Registry(self.system,directory,e)
        self.store=None
        try:
            c=validate(w,self.registry,self.v)
            self.store=GuardedStore(directory/'run.sqlite')
            self.runtime=BoundRuntime(c,self.store,self.registry,e,cancel_grace=.9)
            self.registry.runtime=self.runtime
        except BaseException:
            if self.store:self.store.close()
            self.system.close();raise
    def export(self,label='final'):
        write(self.dir/(label+'-snapshot.json'),self.runtime.snapshot)
        write(self.dir/(label+'-events.json'),self.store.events())

def validate(w,registry=None,v=None):
    # Environment and implementations are host-owned, not submitted by the webview.
    if len(w.get('graph',{}).get('nodes',[]))>64 or len(w.get('graph',{}).get('edges',[]))>128:raise ContractError('GRAPH_LIMIT')
    if w.get('subgraphs')!={}:raise ContractError('SUBGRAPH_NOT_SUPPORTED')
    if w.get('environmentRequirements')!=requirements(w.get('graph',{}).get('nodes',[])):raise ContractError('TRUSTED_REQUIREMENTS_REQUIRED')
    if w.get('inputSchema')!={'type':'object','properties':{},'required':[],'additionalProperties':False} or w.get('outputSchema')!={'type':'string'}:raise ContractError('WORKBENCH_IO_PROFILE')
    for n in w['graph']['nodes']:
        if n['typeId'] not in LABELS:raise ContractError('NODE_UNRESOLVED',n['id'])
        if n['policy']['timeoutMs']>30000:raise ContractError('TIMEOUT_LIMIT')
    v=v or SchemaAdapter(ROOT/'research/02-node-contracts/schemas/contract.schema.json',CATALOG)
    return Contracts(w,request(w),CATALOG,v,registry or Registry(None,HERE,{}))

def layout_checked(layout):
    p006.exact(layout,('version','positions'))
    if layout['version']!='aos-layout/0.1' or not isinstance(layout['positions'],dict) or len(layout['positions'])>128:raise ContractError('LAYOUT_INVALID')
    for id,pos in layout['positions'].items():
        if not isinstance(id,str) or len(id)>100:raise ContractError('LAYOUT_INVALID')
        p006.exact(pos,('x','y'))
        if any(type(pos[k]) not in (int,float) or abs(pos[k])>1000000 for k in ('x','y')):raise ContractError('LAYOUT_INVALID')

class Endpoint(p006.Endpoint):
    def __init__(self,directory,fault):
        super().__init__(directory,fault)
        self.workspace=HERE/'workspace';self.workspace.mkdir(exist_ok=True)
        self.read_ids=[]
    async def request(self,r):
        # Preserve mutation receipt identity. Bound the in-memory read-id replay window
        # so a long-lived desktop session does not fail merely because it polls status.
        while len(self.seen)>=4000 and self.read_ids:
            self.seen.pop(self.read_ids.pop(0),None)
        reply=await super().request(r)
        if isinstance(r,dict) and r.get('op') in ('health','status','events','approvals') and r.get('id') not in self.read_ids:
            self.read_ids.append(r.get('id'))
        return reply
    async def dispatch(self,op,b):
        if op=='approvals':
            p006.exact(b,());self.require_run();rt=self.s.runtime
            result=[]
            for a in rt.snapshot['approvals'].values():
                if a['status']!='pending':continue
                phase,inputs=rt._dependencies(a['key'])
                result.append({**a,'action':{'runId':rt.snapshot['runId'],'revision':rt.snapshot['workflowRevision'],
                  'operationId':rt.snapshot['nodes'][a['key']]['operationId'],'spec':rt.spec(a['key']),'inputs':inputs},
                  'verified':phase=='ready' and rt._fingerprint(a['key'],inputs)==a['fingerprint']})
            return result
        if op=='health':
            p006.exact(b,())
            return {'executorVersion':'p0-07.1','protocol':p006.VERSION,'authority':'C1/SQLite','python':sys.version.split()[0],
              'catalog':read(CATALOG),'labels':LABELS,'defaults':DEFAULTS,'sample':sample(),
              'approvalSample':sample(True),'driverFault':self.driver_fault,'buildProfile':'fixed-trusted-p07'}
        if op=='load':
            if b.get('action')=='run-definition':
                p006.exact(b,('action',));self.require_run();return deepcopy(self.s.runtime.c.w)
            if b.get('action')=='open':
                p006.exact(b,('action','name'));name=b['name'];self.check_name(name)
                return read(self.workspace/(name+'.document.json'))
            if b.get('action')=='save':
                p006.exact(b,('action','name','document'));name=b['name'];self.check_name(name)
                d=b['document'];p006.exact(d,('workflow','layout'));layout_checked(d['layout'])
                # Save incomplete/unknown drafts losslessly; validation is mandatory only for execution.
                p006.SchemaAdapter(ROOT/'research/02-node-contracts/schemas/contract.schema.json',CATALOG).validate(d['workflow'])
                dest=self.workspace/(name+'.document.json');temp=dest.with_suffix('.tmp');write(temp,d);temp.replace(dest)
                # Also materialize the portable execution definition and independent layout.
                write(self.workspace/(name+'.workflow.json'),d['workflow']);write(self.workspace/(name+'.layout.json'),d['layout'])
                return {'saved':name,'workflowDigest':digest(d['workflow'])}
            p006.exact(b,('action','workflow'))
            if b['action']!='validate':raise ContractError('UNKNOWN_LOAD_ACTION')
            w=b['workflow'];validate(w)
            self.loaded={'workflow':deepcopy(w),'token':digest([w,profile_digest()]),'key':uuid.uuid4().hex}
            return {'valid':True,'token':self.loaded['token'],'workflowRevision':w['version']['revision'],'workflowDigest':digest(w)}
        if op=='recover':
            p006.exact(b,())
            if self.s:raise ContractError('RUN_ALREADY_OPEN')
            if not (self.dir/'latest.json').exists():raise ContractError('RUN_NOT_FOUND')
            meta=read(self.dir/'latest.json');w=read(self.dir/'runs'/meta['key']/'workflow.json')
            if read(self.dir/'runs'/meta['key']/'profile.json')['digest']!=profile_digest():raise ContractError('HOST_PROFILE_DRIFT')
            self.loaded={'workflow':w,'token':digest([w,profile_digest()]),'key':meta['key']}
            state=self.begin(True);self.start_driver();return state
        return await super().dispatch(op,b)
    def check_name(self,name):
        if not isinstance(name,str) or not re.fullmatch('[A-Za-z0-9_-]{1,48}',name):raise ContractError('DOCUMENT_NAME_DENIED')
    def begin(self,recover=False):
        if self.s:
            if self.s.runtime.snapshot['state']=='unknown':raise ContractError('UNKNOWN_RUN_REQUIRES_RECONCILIATION')
            if self.s.runtime.snapshot['state'] not in ('succeeded','failed','cancelled','unknown'):raise ContractError('RUN_STILL_ACTIVE')
            if self.driver and not self.driver.done():raise ContractError('DRIVER_STILL_ACTIVE')
            self.s.export();self.s.store.close();self.s.system.close();self.s=None
        if not self.loaded:raise ContractError('LOAD_REQUIRED')
        key=self.loaded['key'];directory=self.dir/'runs'/key
        if directory.exists() and not recover:raise ContractError('CREATE_UNCERTAIN_RECOVER_REQUIRED')
        self.s=Session(directory,self.loaded['workflow'],recover=recover)
        if not recover:write(directory/'profile.json',{'digest':profile_digest()})
        self.cursor=0;self.driver=None;self.driver_fault=None
        temp=self.dir/'latest.tmp';write(temp,{'key':key,'workflowDigest':digest(self.loaded['workflow'])});temp.replace(self.dir/'latest.json')
        return self.s.runtime.snapshot

async def main():
    a=argparse.ArgumentParser();a.add_argument('--session',required=True);a.add_argument('--fault',default='normal');args=a.parse_args()
    directory=Path(args.session).resolve()
    if not directory.is_relative_to(HERE/'evidence'):raise SystemExit('SESSION_PATH_DENIED')
    for _ in range(500):
        if (directory/'worker-gate').exists():break
        await asyncio.sleep(.01)
    else:raise SystemExit('HOST_OWNERSHIP_GATE_TIMEOUT')
    p006.send({'v':p006.VERSION,'kind':'ready','id':'startup','pid':os.getpid(),'version':'p0-07.1'})
    await Endpoint(directory,args.fault).run()
if __name__=='__main__':asyncio.run(main())
