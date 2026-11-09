"""P0-08 inherits reviewed editable-workflow endpoint, IPC and C1; adds D1 only."""
import argparse,asyncio,hashlib,importlib.util,os,sys,time
from pathlib import Path
from copy import deepcopy
from boot import HERE,ROOT,read,write,digest,ContractError,OutcomeError
import model_profile as profile
# P0-07 endpoint imports a profile by this name. Supply the compatible extended profile explicitly.
profile.old.CATALOG=profile.CATALOG
profile.old.HERE=HERE
sys.modules['workbench_profile']=profile
spec=importlib.util.spec_from_file_location('p007_endpoint_reuse',HERE.parent/'p0-07/executor.py')
p007=importlib.util.module_from_spec(spec);spec.loader.exec_module(p007)
from contracts import Contracts
from schema_adapter import SchemaAdapter
from integration import GuardedStore
from mocks import SyntheticSystem,Result
from http_fixture import Fixture
from credentials import Vault
from model_adapter import ModelAdapter
from model_runtime import ModelRuntime

class Registry(p007.Registry):
    def __init__(self,*args,fixture=None,vault=None,alias=None,**kw):
        super().__init__(*args,**kw);self.d1=ModelAdapter(fixture,vault,alias)
    def metadata(self,tid):
        if tid in profile.MODELS:return {'effect':'billable'}
        if tid in ('p08.json-text','p08.join'):return {'effect':'none'}
        return super().metadata(tid)
    async def invoke(self,ctx):
        if ctx.node['typeId'] in profile.MODELS:
            if self.runtime is None:raise ContractError('TRUSTED_CONTROLLER_REQUIRED')
            s=self.runtime.snapshot;n=s['nodes'][ctx.key]
            if s['cancelRequested'] or n['state']!='running' or n['attempts'][-1]['id']!=ctx.attempt_id or self.runtime.spec(ctx.key)!=ctx.node:raise ContractError('MODEL_DISPATCH_IDENTITY_MISMATCH')
            if n['attempts'][-1]['inputs']!=ctx.inputs or n['operationId']!=ctx.operation_id:raise ContractError('MODEL_DISPATCH_INPUT_MISMATCH')
            if ctx.node['policy']['approval']=='always' or self.runtime.c.w['executionPolicy']['approval']=='always':
                a=s['approvals'].get(n.get('approvalId'))
                if not a or a['status']!='consumed' or a['expiresAt']<=time.time() or a['fingerprint']!=self.runtime._fingerprint(ctx.key,ctx.inputs):raise ContractError('APPROVAL_NOT_VALID_AT_MODEL_BOUNDARY')
            if ctx.node['config']['credentialAlias']!='credential:fixture':raise ContractError('CREDENTIAL_ALIAS_UNBOUND')
            return await self.d1.invoke(ctx)
        if ctx.node['typeId']=='p08.json-text':return Result({'out':ctx.inputs['in']['answer']})
        if ctx.node['typeId']=='p08.join':return Result({'out':'\n'.join(ctx.inputs['items'])})
        return await super().invoke(ctx)

def validate(w,registry=None,v=None):
    if len(w.get('graph',{}).get('nodes',[]))>64 or len(w.get('graph',{}).get('edges',[]))>128:raise ContractError('GRAPH_LIMIT')
    if w.get('subgraphs')!={}:raise ContractError('SUBGRAPH_NOT_SUPPORTED')
    if w.get('environmentRequirements')!=profile.requirements(w.get('graph',{}).get('nodes',[])):raise ContractError('TRUSTED_REQUIREMENTS_REQUIRED')
    if w.get('inputSchema')!=profile.obj({}) or w.get('outputSchema')!={'type':'string'}:raise ContractError('WORKBENCH_IO_PROFILE')
    for n in w['graph']['nodes']:
        if n['typeId'] not in profile.LABELS:raise ContractError('NODE_UNRESOLVED')
        if n['policy']['timeoutMs']>30000:raise ContractError('TIMEOUT_LIMIT')
    v=v or SchemaAdapter(ROOT/'research/02-node-contracts/schemas/contract.schema.json',profile.CATALOG)
    return Contracts(w,profile.request(w),profile.CATALOG,v,registry or Registry(None,HERE,{}))

class Session:
    def __init__(self,directory,w,*,recover=False):
        self.dir=directory;directory.mkdir(exist_ok=True,parents=True)
        # Claim before touching manifests, server resources or the run-owned credential target.
        self.store=GuardedStore(directory/'run.sqlite');self.fixture=None;self.vault=Vault();self.system=None
        try:
            self.fixture=Fixture(directory/'http')
            self.alias=self.vault.create_fixture('fixture-'+digest(str(directory.resolve()))[:32])
            write(directory/'owned-credential.json',{'alias':self.alias,'syntheticOnly':True})
            if not recover:
                for name,value in [('workflow',w),('request',profile.request(w)),('environment',profile.environment())]:write(directory/(name+'.json'),value)
            w,r,e=(read(directory/(name+'.json')) for name in ('workflow','request','environment'))
            self.system=SyntheticSystem(directory/'synthetic.sqlite');self.registry=Registry(self.system,directory,e,fixture=self.fixture,vault=self.vault,alias=self.alias)
            c=validate(w,self.registry)
            self.runtime=ModelRuntime(c,self.store,self.registry,e,cancel_grace=.9);self.registry.runtime=self.runtime
        except BaseException:
            self.store.close()
            if self.system:self.system.close()
            if self.fixture:self.fixture.close()
            self.vault.close();raise
    def export(self,label='final'):
        write(self.dir/(label+'-snapshot.json'),self.runtime.snapshot);write(self.dir/(label+'-events.json'),self.store.events())
    def release_resources(self):self.vault.close();self.fixture.close()

def profile_digest():
    paths=[*[HERE/n for n in ('boot.py','executor.py','model_profile.py','model_runtime.py','model_adapter.py','http_fixture.py','credentials.py','windows_adapter.py','mcp_server_entry.py')],
      profile.CATALOG,*[HERE.parent/'p0-03'/n for n in ('runtime.py','contracts.py','store.py','common.py','mocks.py')],
      *[HERE.parent/'p0-04'/n for n in ('integration.py','mcp_client.py','process_host.py','tool_specs.py')],
      HERE.parent/'p0-07/executor.py',HERE.parent/'p0-07/workbench_profile.py',HERE.parent/'p0-06/executor.py',HERE/'sdk-requirements.lock']
    return digest({str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})
p007.validate=validate;p007.Session=Session;p007.profile_digest=profile_digest
class Endpoint(p007.Endpoint):
    def begin(self,recover=False):
        prior=self.s
        result=super().begin(recover)
        if prior:prior.release_resources()
        return result
    async def dispatch(self,op,b):
        if op=='health':
            result=await super().dispatch(op,b)
            result.update(executorVersion='p0-08.1',capabilities=profile.MODELS,
              modelSamples={tid:profile.sample(tid) for tid in profile.MODELS},
              providers=[{'id':'fixture','status':'offline-http-synthetic'},{'id':'openai','status':'unconfigured-authorization-required'},{'id':'anthropic','status':'unconfigured-authorization-required'}])
            return result
        if op=='shutdown':
            result=await super().dispatch(op,b)
            if self.s:self.s.release_resources()
            return result
        return await super().dispatch(op,b)
async def main():
    a=argparse.ArgumentParser();a.add_argument('--session',required=True);a.add_argument('--fault',default='normal');args=a.parse_args();directory=Path(args.session).resolve()
    if not directory.is_relative_to(HERE/'evidence'):raise SystemExit('SESSION_PATH_DENIED')
    for _ in range(500):
        if (directory/'worker-gate').exists():break
        await asyncio.sleep(.01)
    else:raise SystemExit('HOST_OWNERSHIP_GATE_TIMEOUT')
    p007.p006.send({'v':p007.p006.VERSION,'kind':'ready','id':'startup','pid':os.getpid(),'version':'p0-08.1'})
    await Endpoint(directory,args.fault).run()
if __name__=='__main__':asyncio.run(main())
