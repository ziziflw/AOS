"""D2 adapter plus E3 environment implementation. P0-03 C1 remains unchanged."""
import asyncio,hashlib,sqlite3,time
from copy import deepcopy
from pathlib import Path
from bootstrap import HERE,ROOT,read,write,ContractError,OutcomeError
from cases import FIX,SPECS,environment,inputs
from contracts import SchemaClient,Contracts
from runtime import Runtime
from store import StateStore
from mocks import MockRegistry,SyntheticSystem,Result
from mcp_client import MCPClient
from tool_specs import signature,descriptor

class MCPRegistry(MockRegistry):
    def __init__(self,system,directory,binding):
        super().__init__(system); self.dir=Path(directory); self.binding=deepcopy(binding); self.clients=[]; self.runtime=None
    def name(self,n):
        if n['typeId']=='tool.query': return 'structured_result'
        if n['typeId'].startswith('tool.mcp.'): return n['typeId'][9:]
        raise ContractError('NOT_MCP_TOOL')
    def metadata(self,tid):
        if tid=='tool.query': return {'effect':'read'}
        if tid.startswith('tool.mcp.') and tid[9:] in SPECS: return {'effect':SPECS[tid[9:]][2]}
        if tid.startswith('p04.input.') and tid[10:] in SPECS: return {'effect':'none'}
        if tid.startswith('synth.output-') and tid[13:] in SPECS: return {'effect':'none'}
        return super().metadata(tid)
    async def invoke(self,ctx):
        if ctx.node['typeId'].startswith('p04.input.'): return Result({'out':deepcopy(ctx.scope_inputs['arguments'])})
        if ctx.node['typeId']!='tool.query' and not ctx.node['typeId'].startswith('tool.mcp.'): return await super().invoke(ctx)
        if self.runtime is None: raise ContractError('TRUSTED_CONTROLLER_REQUIRED')
        state=self.runtime.snapshot; node=state['nodes'][ctx.key]; spec=self.runtime.spec(ctx.key)
        if node['state']!='running' or node['attempts'][-1]['id']!=ctx.attempt_id or node['operationId']!=ctx.operation_id or spec!=ctx.node:
            raise ContractError('DISPATCH_IDENTITY_MISMATCH')
        name=self.name(spec); effect=SPECS[name][2]
        if state['cancelRequested'] or ctx.cancel.is_set(): raise OutcomeError('CANCEL_BEFORE_MCP',side_effect='not-started')
        if name not in self.binding['extensions']['aos:allowed-tools']: raise ContractError('TOOL_PERMISSION_DENIED')
        if effect in ('write','unknown'):
            aid=node.get('approvalId'); approval=state['approvals'].get(aid)
            if not approval or approval['status']!='consumed' or approval['fingerprint']!=self.runtime._fingerprint(ctx.key,ctx.inputs):
                raise ContractError('APPROVAL_NOT_CONSUMED')
        identity={'runId':state['runId'],'nodeKey':ctx.key,'nodeTypeVersion':spec['typeVersion'],'attemptId':ctx.attempt_id,'attemptNumber':ctx.attempt_no,
                  'operationId':ctx.operation_id,'iteration':ctx.iteration,'adapter':spec['adapter']}
        connection=self.binding['connections']['connection:p04']; launch=self.binding['extensions']['aos:programs'][connection['programRef']]
        directory=self.dir/('mcp-'+str(len(self.clients)+1)); client=MCPClient(directory,launch,[name]); self.clients.append(client)
        started=time.monotonic()
        try:
            await client.open()
            # Handshake can take time. Recheck the consumed authorization at the actual wire boundary.
            current=self.runtime.snapshot
            if current['cancelRequested'] or ctx.cancel.is_set(): raise OutcomeError('MCP_CANCEL_BEFORE_CALL',side_effect='unknown')
            if effect in ('write','unknown'):
                approval=current['approvals'].get(node.get('approvalId'))
                if not approval or approval['status']!='consumed' or approval['expiresAt']<=time.time():
                    raise ContractError('APPROVAL_EXPIRED_BEFORE_MCP')
                if approval['fingerprint']!=self.runtime._fingerprint(ctx.key,ctx.inputs): raise ContractError('APPROVAL_CONTENT_CHANGED')
            # C1 owns node timeout; adapter deadline is slightly earlier so its error preserves side-effect uncertainty.
            timeout=spec['policy']['timeoutMs']/1000-(time.monotonic()-started)-.4
            if timeout<=0: raise OutcomeError('MCP_STARTUP_EXCEEDED_DEADLINE',side_effect='not-started')
            output=await client.call(name,ctx.inputs['args'],identity,cancel=ctx.cancel,timeout=timeout,effect=effect)
            return Result({'out':output})
        except ContractError: raise
        finally: await client.close()
    async def close(self):
        for c in self.clients: await c.close()

class BoundRuntime(Runtime):
    async def _execute(self,key,inputs,attempt_id):
        try: await super()._execute(key,inputs,attempt_id)
        except OutcomeError as exc:
            if exc.code!='LOCAL_PERSISTENCE_FAILURE': raise
            write(self.registry.dir/'worker-storage-failure.json',{'code':exc.code,'key':key,'attemptId':attempt_id,'policy':'fenced store prevents further commits or dispatch'})
    async def drive(self):
        try: return await super().drive()
        except OutcomeError as exc:
            if exc.code=='LOCAL_PERSISTENCE_FAILURE':
                await self.registry.close()
                write(self.registry.dir/'storage-failure.json',{'code':exc.code,'policy':'fail-stop; no new dispatch; last committed snapshot remains authoritative'})
            raise
    def _validate_environment(self):
        e=self.environment; self.c.v.validate(e)
        if e['platform']!={'os':'windows','arch':'x64'}: raise ContractError('TARGET_NOT_VERIFIED')
        if e['profileId']!=self.c.request['environmentProfile']: raise ContractError('ENVIRONMENT_PROFILE_MISMATCH')
        x=e['extensions']
        if x.get('aos:server-artifact-sha256')!=hashlib.sha256((HERE/'synthetic_server.py').read_bytes()).hexdigest(): raise ContractError('SERVER_ARTIFACT_DRIFT')
        for r in self.c.w['environmentRequirements']:
            if r['kind']=='resource':
                if e['resources'].get(r['slot'])!={'mountPath':'memory:synthetic','mode':'read'}: raise ContractError('REAL_RESOURCE_FORBIDDEN')
                continue
            b=e['services'].get(r['slot'])
            if not b or b['adapter']!=r['adapter']: raise ContractError('SERVICE_BINDING_MISMATCH')
            name=b['target']['model']
            ad=self.c.adapters[(b['adapter']['id'],b['adapter']['version'])]
            if b['target']!=ad['capability']['selector']: raise ContractError('CAPABILITY_TARGET_CHANGED')
            if name not in SPECS or name not in x['aos:allowed-tools'] or r['permissions']!=['synthetic:tool:'+name]: raise ContractError('TOOL_PERMISSION_DENIED')
            con=e['connections'].get(b['connectionRef'])
            if not con or con!={'transport':'stdio','programRef':'program:aos-p04-server','environmentRefs':[]}: raise ContractError('SERVER_CONNECTION_DENIED')
            launch=x.get('aos:programs',{}).get(con['programRef'])
            if not launch or not Path(launch['executable']).is_file(): raise ContractError('SERVER_PROGRAM_MISSING')
            if Path(launch['executable']).resolve()!=(HERE/'.venv/Scripts/python.exe').resolve(): raise ContractError('SERVER_COMMAND_DENIED')
            if launch['args']!=['-B','-X','utf8',str(HERE/'synthetic_server.py')]: raise ContractError('SERVER_COMMAND_DENIED')

class GuardedStore(StateStore):
    """Fence dispatch after a local persistence error; never invent a durable terminal state."""
    storage_failed=False
    def commit(self,state,event):
        if self.storage_failed: raise OutcomeError('LOCAL_PERSISTENCE_FAILURE',side_effect='unknown')
        try: return super().commit(state,event)
        except (OSError,sqlite3.Error) as exc:
            self.storage_failed=True
            raise OutcomeError('LOCAL_PERSISTENCE_FAILURE',side_effect='unknown') from exc

class Session:
    def __init__(self,directory,v,name='structured_result',mode='normal',*,change=None,recover=False,hook=None,ttl=300):
        self.dir=Path(directory); self.dir.mkdir(parents=True,exist_ok=True)
        if not recover:
            w,r=inputs(name); e=environment(name,mode)
            if change: change(w,r,e)
            write(self.dir/'workflow.json',w); write(self.dir/'request.json',r); write(self.dir/'environment.json',e)
        w,r,e=(read(self.dir/(n+'.json')) for n in ('workflow','request','environment'))
        self.system=SyntheticSystem(self.dir/'builtin-synthetic.sqlite')
        self.registry=MCPRegistry(self.system,self.dir,e); self.store=None
        try:
            c=Contracts(w,r,FIX/'catalog.json',v,self.registry)
            self.store=GuardedStore(self.dir/'run.sqlite',hook)
            self.runtime=BoundRuntime(c,self.store,self.registry,e,approval_ttl=ttl,cancel_grace=.2)
            self.registry.runtime=self.runtime
        except BaseException:
            if self.store: self.store.close()
            self.system.close(); raise
    def export(self,label='final'):
        write(self.dir/(label+'-snapshot.json'),self.runtime.snapshot)
        write(self.dir/(label+'-events.json'),self.store.events())
        write(self.dir/(label+'-server-ledgers.json'),self.ledgers())
    def ledgers(self):
        rows=[]
        for p in sorted(self.dir.glob('mcp-*/server-ledger.sqlite')):
            db=sqlite3.connect(p)
            try:
                # File creation precedes CREATE TABLE; an observer must wait for the schema commit.
                if db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='records'").fetchone():
                    rows.extend({'directory':p.parent.name,'seq':r[0],'kind':r[1],**__import__('json').loads(r[2])} for r in db.execute('SELECT * FROM records ORDER BY seq'))
            finally: db.close()
        return rows
    async def close(self):
        if not self.store.storage_failed: await self.runtime.close()
        await self.registry.close(); self.export(); self.store.close(); self.system.close()
