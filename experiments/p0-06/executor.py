"""Private inherited stdio endpoint. C1 is imported, never reimplemented here."""
import argparse,asyncio,hashlib,json,os,re,sqlite3,struct,sys,time
from pathlib import Path
from types import SimpleNamespace
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
P03=HERE.parent/'p0-03';P04=HERE.parent/'p0-04';P05=HERE.parent/'p0-05'
for p in (P05,P04,P03):sys.path.insert(0,str(p))
from common import ContractError,read,write,digest
from contracts import Contracts
from schema_adapter import SchemaAdapter
from mocks import MockRegistry,SyntheticSystem
from harness import Session as CoreSession,inputs
from fixtures import FIX as CORE_FIX
from integration import Session as MCPSession,MCPRegistry
from agent_integration import Session as AgentSession,AgentRegistry
from cases import inputs as mcp_inputs,FIX as MCP_FIX
from agent_cases import workflow as agent_workflow,FIX as AGENT_FIX
import mcp_client
from system_layer import LocalMCPHost
VERSION='aos-local/0.1';LIMIT=262144
BUILTINS={'p02-a','serial','parallel','effect','mcp','mcp-delay','mcp-effect','agent','agent-effect','agent-uncancelable'}

mcp_client.ProcessHost=LocalMCPHost

def pairs(items):
    d={}
    for k,v in items:
        if k in d:raise ValueError('duplicate key')
        d[k]=v
    return d
def decode(b):return json.loads(b.decode('utf-8'),object_pairs_hook=pairs,parse_constant=lambda x:(_ for _ in ()).throw(ValueError('nonfinite')))
def exact(body,required,optional=()):
    if not isinstance(body,dict) or not set(required)<=body.keys() or set(body)-set(required)-set(optional):raise ContractError('INVALID_BODY')
def response(id,result=None,error=None):return {'v':VERSION,'kind':'response','id':id,'ok':error is None,**({'error':{'code':error,'retryable':False}} if error else {'result':result})}
def send(v):
    b=json.dumps(v,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
    if not 0<len(b)<=LIMIT:raise ContractError('OUTPUT_SIZE')
    sys.stdout.buffer.write(struct.pack('>I',len(b))+b);sys.stdout.buffer.flush()
def receive():
    n=sys.stdin.buffer.read(4)
    if not n:return None
    if len(n)!=4:raise ContractError('FRAME_TRUNCATED')
    size=struct.unpack('>I',n)[0]
    if not 0<size<=LIMIT:raise ContractError('FRAME_SIZE')
    data=sys.stdin.buffer.read(size)
    if len(data)!=size:raise ContractError('FRAME_TRUNCATED')
    try:return decode(data)
    except (ValueError,UnicodeError):raise ContractError('INVALID_JSON') from None

class Endpoint:
    def __init__(self,session,fault):
        self.dir=session;self.fault=fault;self.s=None;self.v=None;self.driver=None;self.loaded=None;self.cursor=0;self.exit=False
        self.seen={};self.driver_fault=None;self.stream_request_id=None
        self.receipts=sqlite3.connect(session/'ipc-receipts.sqlite',isolation_level=None)
        self.receipts.execute('PRAGMA synchronous=FULL');self.receipts.execute('CREATE TABLE IF NOT EXISTS receipts(id TEXT PRIMARY KEY,digest TEXT,response TEXT)')
    def schema(self,catalog):
        if self.v:self.v.close()
        self.v=SchemaAdapter(ROOT/'research/02-node-contracts/schemas/contract.schema.json',catalog)
    def prepare(self,name):
        if name not in BUILTINS:raise ContractError('BUILTIN_NOT_ALLOWED')
        if self.s:raise ContractError('RUN_ALREADY_OPEN')
        if name.startswith('mcp'):
            op={'mcp':'structured_result','mcp-delay':'delayed_result','mcp-effect':'simulated_effect'}[name]
            w,r=mcp_inputs(op);catalog=MCP_FIX/'catalog.json'
            if name=='mcp-delay':r['inputs']['arguments']['delayMs']=1200
        elif name.startswith('agent'):
            w,r=agent_workflow(skill='effect' if name=='agent-effect' else 'echo',mode='cancel-unsupported' if name=='agent-uncancelable' else 'normal',delay=2200,timeout=9000);catalog=AGENT_FIX/'catalog.json'
        else:w,r,catalog=inputs('a' if name=='p02-a' else name)
        self.schema(catalog)
        registry=MCPRegistry(None,self.dir,{}) if name.startswith('mcp') else AgentRegistry(None,self.dir,{}) if name.startswith('agent') else MockRegistry(None)
        Contracts(w,r,catalog,self.v,registry)
        self.loaded={'builtin':name,'workflowDigest':digest(w),'requestDigest':digest(r),'catalogDigest':hashlib.sha256(catalog.read_bytes()).hexdigest(),'workflow':w,'request':r}
        self.loaded['hostProfileDigest']=digest({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (HERE/'executor.py',HERE/'schema_adapter.py',HERE/'system_layer.py',HERE/'mcp_server_entry.py',HERE/'agent_server_entry.py')})
        self.loaded['token']=digest({k:v for k,v in self.loaded.items() if k not in ('workflow','request')})
        return {k:v for k,v in self.loaded.items() if k not in ('workflow','request')}
    def begin(self,recover=False):
        directory=self.dir/'run';meta=self.dir/'run-manifest.json'
        if recover:
            if not meta.exists():raise ContractError('RUN_NOT_FOUND')
            locked=read(meta);self.prepare(locked['builtin'])
            if self.loaded['token']!=locked['token']:raise ContractError('INSTALLED_DEFINITION_DRIFT')
        elif meta.exists():raise ContractError('RUN_ALREADY_EXISTS')
        if not self.loaded:raise ContractError('LOAD_REQUIRED')
        name=self.loaded['builtin']
        if not recover:
            temp=meta.with_suffix('.tmp');write(temp,self.loaded);temp.replace(meta)
        if name.startswith('agent'):
            service=read(self.dir/'services.json')
            if set(service)!={'agentA'} or not re.fullmatch(r'http://127\.0\.0\.1:[0-9]{1,5}',service['agentA']):raise ContractError('SERVICE_NOT_ALLOWED')
            hosts={k:SimpleNamespace(endpoint=v) for k,v in service.items()}
            self.s=AgentSession(directory,self.v,hosts,skill='effect' if name=='agent-effect' else 'echo',mode='cancel-unsupported' if name=='agent-uncancelable' else 'normal',delay=2200,timeout=9000,recover=recover)
        elif name.startswith('mcp'):
            op={'mcp':'structured_result','mcp-delay':'delayed_result','mcp-effect':'simulated_effect'}[name]
            def change(w,r,e):
                if name=='mcp-delay':r['inputs']['arguments']['delayMs']=1200
                e['extensions']['aos:programs']['program:aos-p04-server']['p006:wrapperSha256']=hashlib.sha256((HERE/'mcp_server_entry.py').read_bytes()).hexdigest()
            self.s=MCPSession(directory,self.v,op,mode='spawn-child' if name=='mcp-delay' else 'normal',change=change,recover=recover)
        else:
            w,r,c=inputs('a' if name=='p02-a' else name)
            self.s=CoreSession(directory,self.v,workflow=w,request=r,catalog_path=c,recover=recover,
                               plan={'B':{'delay':.6},'C':{'delay':.6}} if name=='parallel' else None)
            self.s.runtime.cancel_grace=.9
        return self.s.runtime.snapshot
    def start_driver(self):
        if self.s and (self.driver is None or self.driver.done()):
            self.driver=asyncio.create_task(self.s.runtime.drive())
            def finished(t):
                if not t.cancelled() and t.exception():
                    self.driver_fault='C1_DRIVER_FAILED';print('C1 driver failed; last committed state remains authoritative',file=sys.stderr,flush=True)
            self.driver.add_done_callback(finished)
    def require_run(self):
        if not self.s:raise ContractError('NO_OPEN_RUN')
    def diagnostic(self):
        if self.v and hasattr(self.v,'process'):
            try:self.v.process.wait(timeout=.2)
            except __import__('subprocess').TimeoutExpired:return
            print('Schema bridge exit: '+str(self.v.process.returncode)+' '+self.v.process.stderr.read()[:3000],file=sys.stderr,flush=True)
    async def dispatch(self,op,b):
        if op=='health':
            exact(b,());return {'executorVersion':'p0-06.1','protocol':VERSION,'python':sys.version.split()[0],'pid':os.getpid(),'authority':'C1/SQLite','singleRunPerSession':True,'driverFault':self.driver_fault}
        if op=='load':exact(b,('builtin',));return self.prepare(b['builtin'])
        if op=='create':
            exact(b,('token',))
            if not self.loaded or b['token']!=self.loaded['token']:raise ContractError('LOAD_TOKEN_MISMATCH')
            state=self.begin();self.start_driver();return state
        if op=='recover':exact(b,());state=self.begin(recover=True);self.start_driver();return state
        if op=='shutdown':
            exact(b,('mode',))
            if b['mode'] not in ('cancel','suspend'):raise ContractError('SHUTDOWN_MODE')
            if self.s:
                if b['mode']=='cancel':
                    self.s.runtime.cancel();self.start_driver()
                    await asyncio.wait_for(asyncio.shield(self.driver),4)
                self.s.export('shutdown')
            self.exit=True;return {'durable':True,'mode':b['mode'],'remoteTaskStopped':'unconfirmed','run':self.s.runtime.snapshot if self.s else None}
        self.require_run()
        if op=='status':exact(b,());return self.s.runtime.snapshot
        if op=='events':
            exact(b,('after',));after=b['after']
            if type(after)!=int or after<0:raise ContractError('INVALID_CURSOR')
            events=[x for x in self.s.store.events() if x['seq']>after][:16]
            return {'runId':self.s.runtime.snapshot['runId'],'events':events,'lastSeq':events[-1]['seq'] if events else after,'authoritySeq':self.s.runtime.snapshot['seq']}
        if op=='approvals':exact(b,());return [a for a in self.s.runtime.snapshot['approvals'].values() if a['status']=='pending']
        if op=='approve':
            exact(b,('approvalId','fingerprint','decision'))
            if type(b['decision'])!=bool:raise ContractError('INVALID_DECISION')
            self.s.runtime.approve(b['approvalId'],b['fingerprint'],b['decision']);self.start_driver();return self.s.runtime.snapshot
        if op=='cancel':exact(b,());self.s.runtime.cancel();self.start_driver();return self.s.runtime.snapshot
        raise ContractError('UNKNOWN_COMMAND')
    async def request(self,r):
        rid=r.get('id','') if isinstance(r,dict) else ''
        try:
            exact(r,('v','kind','id','op','body'))
            if r['v']!=VERSION or r['kind']!='request' or not isinstance(rid,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}',rid) or not isinstance(r['op'],str):raise ContractError('INVALID_ENVELOPE')
            fingerprint=digest(r)
            if rid in self.seen and self.seen[rid]!=fingerprint:raise ContractError('REQUEST_ID_CONFLICT')
            if rid not in self.seen and len(self.seen)>=4096:raise ContractError('REQUEST_HISTORY_LIMIT')
            self.seen[rid]=fingerprint
            row=self.receipts.execute('SELECT digest,response FROM receipts WHERE id=?',(rid,)).fetchone()
            if row:
                if row[0]!=fingerprint:raise ContractError('REQUEST_ID_CONFLICT')
                return json.loads(row[1])
            value=await self.dispatch(r['op'],r['body']);reply=response(rid,value)
            if r['op'] in ('create','recover'):self.stream_request_id=rid
            # Reads remain fresh; mutation IDs are durable across host restart.
            if r['op'] in ('create','approve','cancel'):
                self.receipts.execute('INSERT INTO receipts VALUES(?,?,?)',(rid,fingerprint,json.dumps(reply)))
            return reply
        except ContractError as e:
            self.diagnostic()
            return response(rid,error=e.code)
        except Exception as e:
            self.diagnostic()
            print('IPC command rejected: '+type(e).__name__,file=sys.stderr)
            return response(rid,error='INTERNAL_OR_CONTRACT_ERROR')
    async def events(self):
        while not self.exit:
            if self.s:
                for e in self.s.store.events():
                    if e['seq']>self.cursor:
                        send({'v':VERSION,'kind':'event','id':self.stream_request_id,'runId':self.s.runtime.snapshot['runId'],'seq':e['seq'],'event':e});self.cursor=e['seq']
            await asyncio.sleep(.03)
    async def run(self):
        pump=asyncio.create_task(self.events())
        try:
            while True:
                try:r=await asyncio.to_thread(receive)
                except ContractError as e:send(response('',error=e.code));break
                if r is None:break
                if self.fault=='late-response' and r.get('op')=='health':send(response('expired-request',{'stale':True}))
                reply=await self.request(r)
                if self.exit:
                    # Same event-loop turn: no driver can write after close, and ACK follows DB close.
                    if self.s:self.s.store.close();self.s.system.close()
                    self.receipts.close()
                    if self.v:self.v.close()
                    send(reply);sys.stderr.flush();os._exit(0)
                send(reply)
        finally:
            pump.cancel();await asyncio.gather(pump,return_exceptions=True)
            if self.s:self.s.export('disconnect')
            # Preserve durable C1 intent/approvals. Do not invent terminal facts on EOF.
            self.receipts.close()
            if self.v:self.v.close()
            sys.stdout.flush();sys.stderr.flush()
            os._exit(0)

async def main():
    ap=argparse.ArgumentParser();ap.add_argument('--session',required=True);ap.add_argument('--fault',default='normal',choices=('normal','init-fail','startup-timeout','late-response'));a=ap.parse_args()
    directory=Path(a.session).resolve()
    if not directory.is_relative_to(HERE/'evidence'):raise SystemExit('SESSION_PATH_DENIED')
    for _ in range(500):
        if (directory/'worker-gate').exists():break
        await asyncio.sleep(.01)
    else:raise SystemExit('HOST_OWNERSHIP_GATE_TIMEOUT')
    if a.fault=='init-fail':raise SystemExit(81)
    if a.fault=='startup-timeout':await asyncio.sleep(30)
    send({'v':VERSION,'kind':'ready','id':'startup','pid':os.getpid(),'version':'p0-06.1'})
    await Endpoint(directory,a.fault).run()
if __name__=='__main__':asyncio.run(main())
