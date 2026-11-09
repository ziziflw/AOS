"""Real Rust host / private framed executor boundary; no paid services."""
import asyncio,hashlib,json,os,queue,sqlite3,struct,subprocess,sys,threading,time,traceback,unittest
from datetime import datetime,timezone
from pathlib import Path
from copy import deepcopy
from supervisor import ExternalAgent,alive
from common import read,write
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
HOST=HERE/'host/target/debug/host-probe.exe';WINDOW=HERE/'host/target/debug/host-window.exe';V='aos-local/0.1';EVIDENCE=None
TERMINAL={'succeeded','failed','cancelled','unknown','skipped'}
def dbstate(directory):
    db=sqlite3.connect(directory/'run/run.sqlite')
    try:return json.loads(db.execute('SELECT state FROM snapshot WHERE id=1').fetchone()[0])
    finally:db.close()
class Driver:
    def __init__(self,directory,role='approver',fault='normal'):
        self.dir=directory;directory.mkdir(parents=True,exist_ok=True);self.i=0;self.events=[];self.q=queue.Queue()
        self.log=(directory/'driver.jsonl').open('a',encoding='utf-8');self.stderr=(directory/'host-stderr.log').open('ab')
        self.p=subprocess.Popen([str(HOST),str(HERE),str(directory),role,fault,'test'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=self.stderr,text=True,encoding='utf-8',creationflags=subprocess.CREATE_NO_WINDOW)
        def reader():
            for line in self.p.stdout:
                try:self.q.put(json.loads(line))
                except ValueError:self.q.put({'invalid':line})
            self.q.put(None)
        threading.Thread(target=reader,daemon=True).start()
    def record(self,direction,msg):self.log.write(json.dumps({'direction':direction,'message':msg},ensure_ascii=False)+'\n');self.log.flush()
    def call(self,op,body=None,id=None):
        self.i+=1;r={'v':V,'kind':'request','id':id or 'request-'+str(self.i),'op':op,'body':{} if body is None else body};self.record('test-to-host',r)
        self.p.stdin.write(json.dumps(r)+'\n');self.p.stdin.flush()
        return self.reply(r['id'])
    def reply(self,id):
        deadline=time.monotonic()+25
        while time.monotonic()<deadline:
            v=self.q.get(timeout=max(.1,deadline-time.monotonic()));self.record('host-to-test',v)
            if v is None:raise RuntimeError('Host exited')
            if v.get('kind')=='response':
                if v['id']!=id:raise AssertionError('Unexpected response identity')
                return v
            self.events.append(v)
        raise TimeoutError('Host response')
    def good(self,op,body=None,id=None):
        r=self.call(op,body,id)
        if not r['ok']:raise AssertionError(r)
        return r['result']
    def start(self):return self.good('host.start')
    def create(self,builtin):
        p=self.good('load',{'builtin':builtin});return self.good('create',{'token':p['token']},id='create-run')
    def wait(self,predicate=lambda s:s['state'] in TERMINAL):
        deadline=time.monotonic()+14
        while time.monotonic()<deadline:
            s=self.good('status')
            if predicate(s):return s
            time.sleep(.025)
        raise AssertionError('State predicate timeout: '+json.dumps(s))
    def crash(self):
        if self.p.poll() is None:self.p.kill();self.p.wait(timeout=5)
    def close(self):
        if self.p.poll() is None:
            try:self.call('host.stop',{'mode':'suspend'})
            except (OSError,RuntimeError,AssertionError,queue.Empty):pass
            self.p.stdin.close()
            try:self.p.wait(timeout=5)
            except subprocess.TimeoutExpired:self.crash()
        self.p.stdout.close()
        if not self.p.stdin.closed:self.p.stdin.close()
        self.stderr.close();self.log.close()
class HostTests(unittest.TestCase):
    def setUp(self):
        self.dir=EVIDENCE/self._testMethodName;self.dir.mkdir();self.drivers=[];self.agents=[];self.checks=[]
    def eq(self,a,b,label):
        self.checks.append({'label':label,'expected':deepcopy(b),'actual':deepcopy(a),'passed':a==b});write(self.dir/'assertions.json',self.checks);self.assertEqual(a,b,label)
    def driver(self,name='session',**kw):
        d=Driver(self.dir/name,**kw);self.drivers.append(d);return d
    def agent(self,d):
        a=ExternalAgent(d.dir/'external-agent');asyncio.run(a.start());self.agents.append(a);write(d.dir/'services.json',{'agentA':a.endpoint});return a
    def tasks(self,a):
        db=sqlite3.connect(a.dir/'agent.sqlite')
        try:return [json.loads(x[0]) for x in db.execute('SELECT body FROM tasks')]
        finally:db.close()
    def tearDown(self):
        for d in reversed(self.drivers):d.close()
        for a in self.agents:asyncio.run(a.close())
        pids=set()
        for p in self.dir.rglob('host-trace.jsonl'):
            for line in p.read_text().splitlines():
                v=json.loads(line)
                for k in ('launcherPid','actualPid'):
                    if k in v:pids.add(v[k])
        for p in self.dir.rglob('process.jsonl'):
            for line in p.read_text().splitlines():
                v=json.loads(line)
                for k in ('pid','launcherPid','actualServerPid'):
                    if isinstance(v.get(k),int):pids.add(v[k])
                pids.update(x for x in v.get('pids',[]) if isinstance(x,int))
        for a in self.agents:pids.update(a.pids)
        for p in self.dir.rglob('server-ledger.sqlite'):
            db=sqlite3.connect(p)
            try:
                if db.execute("SELECT name FROM sqlite_master WHERE name='records'").fetchone():
                    for (body,) in db.execute('SELECT body FROM records'):
                        row=json.loads(body)
                        for k in ('pid','childPid'):
                            if isinstance(row.get(k),int):pids.add(row[k])
            finally:db.close()
        deadline=time.monotonic()+3
        while any(alive(p) for p in pids) and time.monotonic()<deadline:time.sleep(.03)
        result=[{'pid':p,'alive':alive(p)} for p in sorted(pids)];write(self.dir/'owned-process-check.json',result)
        self.assertFalse([x for x in result if x['alive']],'Only owned PID checks; no name-based cleanup')
    def test_T01_health_and_start_failures(self):
        d=self.driver();d.start();h=d.good('health');self.eq(h['authority'],'C1/SQLite','health uses actual child')
        self.eq(d.good('host.start')['alreadyStarted'],True,'duplicate start is idempotent')
        for fault in ('init-fail','startup-timeout'):
            f=self.driver(fault,fault=fault);self.eq(f.call('host.start')['ok'],False,'startup rejected '+fault)
    def test_T02_original_contract_loading(self):
        d=self.driver();d.start();p=d.good('load',{'builtin':'p02-a'})
        self.eq(p['workflowDigest'],__import__('common').digest(read(ROOT/'research/02-node-contracts/examples/scenario-a.workflow.json')),'original P0-02 bytes interpreted without new dialect')
        self.eq(d.call('create',{'token':'changed'})['error']['code'],'LOAD_TOKEN_MISMATCH','fixed definition digest')
        self.eq(d.call('load',{'builtin':'C:\\arbitrary.ps1'})['error']['code'],'BUILTIN_NOT_ALLOWED','no path/script loading')
        from schema_adapter import SchemaAdapter
        from contracts import SchemaClient
        from common import ContractError
        schema=ROOT/'research/02-node-contracts/schemas/contract.schema.json';catalog=ROOT/'experiments/p0-03/fixtures/catalog.json'
        native=SchemaAdapter(schema,catalog);old=SchemaClient(schema,catalog)
        try:
            base=read(ROOT/'research/02-node-contracts/examples/scenario-a.workflow.json')
            examples=[base,read(catalog),read(ROOT/'research/02-node-contracts/examples/scenario-a.run-request.json')]
            for mutation in ('missing','version','null','future'):
                x=deepcopy(base)
                if mutation=='missing':del x['workflowId']
                if mutation=='version':x['schemaVersion']='99.0'
                if mutation=='null':x['graph']=None
                if mutation=='future':x['arbitraryFutureField']=True
                examples.append(x)
            for i,x in enumerate(examples):
                results=[]
                for validator in (old,native):
                    try:validator.validate(x);results.append(True)
                    except ContractError:results.append(False)
                self.eq(results[0],results[1],'original schema validator differential case '+str(i))
        finally:old.close()
    def test_T03_existing_core_serial_parallel(self):
        for name in ('serial','parallel'):
            d=self.driver(name);d.start();d.create(name);s=d.wait();self.eq(s['state'],'succeeded','actual C1 '+name)
            self.eq(all(n['state']=='succeeded' for n in s['nodes'].values()),True,'actual node terminals '+name)
            events=d.good('events',{'after':0});self.eq(events['events'][0]['seq'],1,'events originate from durable C1 sequence')
    def test_T04_real_mcp_through_host(self):
        d=self.driver();d.start();d.create('mcp');s=d.wait();self.eq(s['state'],'succeeded','real MCP via Rust/executor')
        logs=list(d.dir.rglob('protocol.jsonl'));self.eq(bool(logs),True,'actual MCP wire trace exists')
        self.eq(any('tools/call' in p.read_text() for p in logs),True,'official ClientSession sends real tool call')
    def test_T05_real_a2a_through_host(self):
        d=self.driver();a=self.agent(d);d.start();d.create('agent');s=d.wait()
        self.eq(s['state'],'succeeded','actual A2A task via host');self.eq(len(self.tasks(a)),1,'exactly one remote task')
        self.eq(s['nodes']['main/agent']['external']['taskId'],self.tasks(a)[0]['id'],'C1 stores original task identity')
        effect=self.driver('controlled-agent');a2=self.agent(effect);effect.start();effect.create('agent-effect');effect.wait(lambda s:s['state']=='waiting-approval')
        self.eq(self.tasks(a2),[],'controlled Agent not submitted before host approval')
        pending=effect.good('approvals')[0];effect.good('approve',{'approvalId':pending['id'],'fingerprint':pending['fingerprint'],'decision':True})
        self.eq(effect.wait()['state'],'succeeded','real effect Agent after host approval');self.eq(len(self.tasks(a2)),1,'one controlled Agent task')
    def test_T06_invalid_frames_and_limit(self):
        d=self.driver();d.start()
        self.eq(d.call('health',{'unexpected':'value'})['error']['code'],'INVALID_BODY','strict known command body')
        self.eq(d.call('shell',{'command':'echo denied'})['error']['code'],'UNKNOWN_COMMAND','no arbitrary command')
        for name,data,code in (
            ('bad-json',b'{','INVALID_JSON'),('duplicate',b'{"id":"x","id":"y"}','INVALID_JSON'),
            ('utf8',b'\xff','INVALID_JSON'),('size',None,'FRAME_SIZE'),('truncated',b'abc','FRAME_TRUNCATED'),
            ('exact-limit',json.dumps({'v':V,'kind':'request','id':'x','op':'health','body':{'padding':''}},separators=(',',':')).encode().replace(b'"padding":""',b'"padding":"'+b'x'*(262144-len(json.dumps({'v':V,'kind':'request','id':'x','op':'health','body':{'padding':''}},separators=(',',':')).encode()))+b'"'),'INVALID_BODY'),
            ('future',json.dumps({'v':V,'kind':'request','id':'x','op':'health','body':{},'future':True}).encode(),'INVALID_BODY')):
            directory=self.dir/name;directory.mkdir();(directory/'worker-gate').write_text('test-owned')
            with (directory/'stderr.log').open('wb') as err:
                p=subprocess.Popen([str(HERE/'.venv/Scripts/python.exe'),'-B',str(HERE/'executor.py'),'--session',str(directory)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=err,creationflags=subprocess.CREATE_NO_WINDOW)
                try:
                    n=struct.unpack('>I',p.stdout.read(4))[0];ready=json.loads(p.stdout.read(n));self.eq(ready['kind'],'ready','private endpoint ready '+name)
                    frame=struct.pack('>I',262145) if data is None else struct.pack('>I',len(data)+(1 if name=='truncated' else 0))+data
                    write(directory/'input.json',{'hex':frame.hex(),'expectedError':code});p.stdin.write(frame);p.stdin.close()
                    n=struct.unpack('>I',p.stdout.read(4))[0];reply=json.loads(p.stdout.read(n));write(directory/'response.json',reply)
                    self.eq(reply['error']['code'],code,'actual framed boundary '+name);p.wait(timeout=5)
                finally:
                    if p.poll() is None:p.kill();p.wait()
                    p.stdout.close()
        d.p.stdin.write('x'*262145+'\n');d.p.stdin.flush();self.eq(d.reply('')['error']['code'],'FRAME_SIZE','Rust ingress size cap')
    def test_T07_order_correlation_idempotency(self):
        d=self.driver(fault='late-response');d.start();d.good('health');self.eq(any(x.get('code')=='UNMATCHED_RESPONSE' for x in d.events),True,'late response never correlated to current health')
        p=d.good('load',{'builtin':'serial'});r1=d.good('create',{'token':p['token']},id='stable-create');r2=d.good('create',{'token':p['token']},id='stable-create')
        self.eq(r1['runId'],r2['runId'],'duplicate create does not create a second run')
        self.eq(d.call('create',{'token':'changed'},id='stable-create')['error']['code'],'REQUEST_ID_CONFLICT','same ID changed operation rejected')
        final=d.wait();cursor=0;all_events=[]
        while cursor<final['seq']:
            page=d.good('events',{'after':cursor});self.assertTrue(page['events']);all_events+=page['events'];cursor=page['lastSeq']
        self.eq([e['seq'] for e in all_events],list(range(1,final['seq']+1)),'durable replay has no gaps or duplicates')
        self.eq(d.good('events',{'after':final['seq']})['events'],[],'explicit resume cursor')
        self.eq(all(e['id']=='stable-create' for e in d.events if e.get('kind')=='event'),True,'event stream correlated to creating request; not claimed as exact causation')
    def test_T08_backend_approval_permissions(self):
        viewer=self.driver('viewer',role='viewer');self.eq(viewer.call('host.start')['error']['code'],'PERMISSION_DENIED','viewer cannot manage process')
        op=self.driver('operator',role='operator');op.start();op.create('effect');op.wait(lambda s:s['state']=='waiting-approval')
        pending=op.good('approvals')[0];body={'approvalId':pending['id'],'fingerprint':pending['fingerprint'],'decision':True}
        self.eq(op.call('approve',body)['error']['code'],'PERMISSION_DENIED','operator cannot approve even with fingerprint')
        self.eq(dbstate(op.dir)['nodes']['main/B']['state'],'waiting-approval','backend gate not UI button')
        d=self.driver('approved');d.start();d.create('effect');d.wait(lambda s:s['state']=='waiting-approval');a=d.good('approvals')[0]
        self.eq(d.call('approve',{'approvalId':a['id'],'fingerprint':'old','decision':True})['ok'],False,'stale operation fingerprint rejected')
        b={'approvalId':a['id'],'fingerprint':a['fingerprint'],'decision':True};d.good('approve',b,id='decision');d.good('approve',b,id='decision');s=d.wait()
        self.eq(s['state'],'succeeded','valid backend grant dispatches once');self.eq(len(s['nodes']['main/B']['attempts']),1,'duplicate approval creates no new attempt')
        denied=self.driver('denied');denied.start();denied.create('effect');denied.wait(lambda s:s['state']=='waiting-approval');a=denied.good('approvals')[0]
        denied.good('approve',{'approvalId':a['id'],'fingerprint':a['fingerprint'],'decision':False});self.eq(denied.wait()['state'],'failed','rejection blocks effect')
        mcp=self.driver('controlled-mcp');mcp.start();mcp.create('mcp-effect');mcp.wait(lambda s:s['state']=='waiting-approval')
        self.eq(list(mcp.dir.rglob('server-ledger.sqlite')),[],'real MCP process/tool not launched before approval')
        a=mcp.good('approvals')[0];mcp.good('approve',{'approvalId':a['id'],'fingerprint':a['fingerprint'],'decision':True});self.eq(mcp.wait()['state'],'succeeded','controlled MCP effect through host grant')
        db=sqlite3.connect(next(mcp.dir.rglob('server-ledger.sqlite')))
        try:self.eq(db.execute("SELECT count(*) FROM records WHERE kind='effect-committed'").fetchone()[0],1,'real independent MCP synthetic effect once')
        finally:db.close()
    def test_T09_cancel_and_coordinated_close(self):
        d=self.driver();d.start();d.create('parallel');d.wait(lambda s:any(n['state']=='running' for k,n in s['nodes'].items() if k in ('main/B','main/C')))
        d.good('cancel');s=d.wait();self.eq(s['state'],'cancelled','cooperative cancel actual runtime')
        self.eq(s['nodes']['main/D']['outputs'],{},'late output does not release join')
        self.eq(d.good('host.stop',{'mode':'cancel'})['durable'],True,'cancel then shutdown ack')
        pending=self.driver('approval-cancel');pending.start();pending.create('effect');pending.wait(lambda s:s['state']=='waiting-approval');a=pending.good('approvals')[0]
        pending.good('cancel');self.eq(pending.wait()['state'],'cancelled','waiting approval cancelled')
        self.eq(pending.call('approve',{'approvalId':a['id'],'fingerprint':a['fingerprint'],'decision':True})['ok'],False,'old approval invalid after cancel')
        normal=self.driver('normal-host-exit');normal.start();normal.create('serial');normal.wait();normal.p.stdin.close();normal.p.wait(timeout=6)
        trace=[json.loads(x) for x in (normal.dir/'host-trace.jsonl').read_text().splitlines()]
        self.eq(any(x.get('kind')=='normal-host-exit-coordination' and x['acknowledged'] for x in trace),True,'normal host EOF coordinates before process cleanup')
        self.eq([x['activeAfterStop'] for x in trace if x['kind']=='owned-job-stopped'],[0],'whole owned Job verified empty')
    def test_T10_executor_crash_keeps_committed_results(self):
        d=self.driver();d.start();d.create('mcp-delay')
        d.wait(lambda s:s['nodes']['main/tool']['state']=='running' and any('tools/call' in p.read_text() for p in d.dir.rglob('protocol.jsonl')))
        before=dbstate(d.dir);write(self.dir/'before-crash.json',before);d.good('host.crash-worker')
        self.eq(d.call('status')['ok'],False,'host reports lost process, not invented node terminal')
        d.start();s=d.good('recover');s=d.wait();write(self.dir/'after-recovery.json',s)
        self.eq(s['runId'],before['runId'],'same run after process crash');self.eq(s['nodes']['main/tool']['state'],'unknown','unconfirmed tool result not repeated')
        self.eq(s['nodes']['main/input']['state'],'succeeded','committed input retained')
        self.eq(len(s['nodes']['main/tool']['attempts']),1,'no blind retry after crash')
    def test_T11_host_restart_and_approval_recovery(self):
        d=self.driver();d.start();d.create('effect');s=d.wait(lambda s:s['state']=='waiting-approval');before=s;d.crash()
        restored=self.driver();restored.start();restored.good('recover');s=restored.wait(lambda s:s['state']=='waiting-approval')
        self.eq(s['runId'],before['runId'],'host restart same run identity');self.eq(s['approvals'],before['approvals'],'pending approval never automatically granted')
        a=restored.good('approvals')[0];restored.good('approve',{'approvalId':a['id'],'fingerprint':a['fingerprint'],'decision':True});s=restored.wait()
        self.eq(s['state'],'succeeded','explicit decision after restart')
        restored.good('host.stop',{'mode':'suspend'});again=self.driver();again.start();again.good('recover');s2=again.wait()
        self.eq(s2['nodes']['main/B']['attempts'],s['nodes']['main/B']['attempts'],'confirmed effect not replayed on second restart')
    def test_T12_concurrent_claim_is_rejected(self):
        d=self.driver();d.start();d.create('effect');d.wait(lambda s:s['state']=='waiting-approval')
        second=self.driver();second.start();r=second.call('recover');self.eq(r['error']['code'],'CONTROLLER_ALREADY_OWNED','second executor cannot claim same SQLite authority')
        d.good('host.stop',{'mode':'suspend'});self.eq(second.good('recover')['runId'],dbstate(d.dir)['runId'],'lock released by owned process termination')
    def test_T13_remote_task_survives_host_and_query_resume(self):
        d=self.driver();a=self.agent(d);d.start();d.create('agent-uncancelable');s=d.wait(lambda s:bool(s['nodes']['main/agent'].get('external',{}).get('taskId')))
        old=s['nodes']['main/agent'];d.crash();self.eq(alive(a.pids[-1]),True,'external Agent not killed with host Job')
        deadline=time.monotonic()+5
        while self.tasks(a)[0]['status']['state']!='TASK_STATE_COMPLETED' and time.monotonic()<deadline:time.sleep(.03)
        self.eq(self.tasks(a)[0]['status']['state'],'TASK_STATE_COMPLETED','local process stop does not cancel external task')
        resumed=self.driver();resumed.start();resumed.good('recover');after=resumed.wait();new=after['nodes']['main/agent']
        self.eq(after['state'],'succeeded','query-only recovery verifies original task');self.eq(new['external']['taskId'],old['external']['taskId'],'task ID fixed')
        self.eq(new['attempts'][-1]['id'],old['attempts'][-1]['id'],'attempt not recreated');self.eq(len(self.tasks(a)),1,'no second SendMessage')
        normal=self.driver('coordinated');a2=self.agent(normal);normal.start();normal.create('agent');state=normal.wait(lambda s:bool(s['nodes']['main/agent'].get('external',{}).get('taskId')))
        stop=normal.good('host.stop',{'mode':'suspend'});self.eq(stop['remoteTaskStopped'],'unconfirmed','normal close does not invent remote cancellation')
        self.eq(alive(a2.pids[-1]),True,'Agent survives coordinated local shutdown')
        self.eq(dbstate(normal.dir)['nodes']['main/agent']['external']['taskId'],state['nodes']['main/agent']['external']['taskId'],'normal close preserves original external identity')
        normal.start();normal.good('recover');self.eq(normal.wait()['state'],'succeeded','normal shutdown resumes only original task query')
    def test_T14_owned_mcp_cleanup_and_remote_cancel_interpretation(self):
        d=self.driver('mcp');d.start();d.create('mcp-delay');d.wait(lambda s:s['nodes']['main/tool']['state']=='running' and any('tools/call' in p.read_text() for p in d.dir.rglob('protocol.jsonl')))
        d.good('host.stop',{'mode':'suspend'});self.eq(d.call('health')['ok'],False,'owned executor stopped with tool descendants')
        a_driver=self.driver('remote');a=self.agent(a_driver);a_driver.start();a_driver.create('agent-uncancelable');a_driver.wait(lambda s:bool(s['nodes']['main/agent'].get('external',{}).get('taskId')))
        a_driver.good('cancel');state=a_driver.wait();self.eq(state['state'],'unknown','unsupported remote cancellation never falsely cancelled')
        self.eq(state['nodes']['main/agent']['outputs'],{},'late remote result excluded');a_driver.good('host.stop',{'mode':'cancel'})
        self.eq(alive(a.pids[-1]),True,'external supervisor lifetime remains independent')
    def test_T15_real_tauri_window_ipc(self):
        if not WINDOW.exists():self.skipTest('Actual Tauri binary unavailable; not replaced by probe test')
        directory=self.dir/'window';directory.mkdir();log=(directory/'window-stderr.log').open('wb')
        p=subprocess.Popen([str(WINDOW),str(HERE),str(directory),'selftest'],stdout=log,stderr=log,creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            p.wait(timeout=55);self.eq(p.returncode,0,'real Tauri process exits after WebView selftest')
            report=read(directory/'window-report.json');self.eq(report['passed'],True,'real JS invoke crossed Tauri/Rust/Python');self.eq(dbstate(directory)['state'],'succeeded','independent SQLite confirmation of UI report')
            self.eq((directory/'webview-profile/EBWebView').is_dir(),True,'actual WebView2 data isolated inside experiment session')
            bridge=[json.loads(x) for x in (directory/'window-bridge.jsonl').read_text().splitlines()]
            self.eq(any(x['op']=='approve' and x['response']['ok'] for x in bridge),True,'actual backend command trace corroborates approval')
        finally:
            if p.poll() is None:p.kill();p.wait()
            log.close()
class EvidenceResult(unittest.TextTestResult):
    records=[]
    def addSuccess(self,test):self.records.append({'test':test.id(),'status':'passed'});super().addSuccess(test)
    def addFailure(self,test,err):self.records.append({'test':test.id(),'status':'failed','traceback':''.join(traceback.format_exception(*err))});super().addFailure(test,err)
    def addError(self,test,err):self.records.append({'test':test.id(),'status':'error','traceback':''.join(traceback.format_exception(*err))});super().addError(test,err)
    def addSkip(self,test,reason):self.records.append({'test':test.id(),'status':'unverified','reason':reason});super().addSkip(test,reason)
def main():
    global EVIDENCE
    EVIDENCE=HERE/'evidence'/('suite-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));EVIDENCE.mkdir(parents=True)
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(HostTests)
    if len(sys.argv)>1:suite=unittest.defaultTestLoader.loadTestsFromNames(sys.argv[1:],HostTests)
    with (EVIDENCE/'unittest.log').open('w',encoding='utf-8') as f:result=unittest.TextTestRunner(stream=f,verbosity=2,resultclass=EvidenceResult).run(suite)
    summary={'testsRun':result.testsRun,'passed':sum(r['status']=='passed' for r in EvidenceResult.records),'failures':len(result.failures),'errors':len(result.errors),'unverified':len(result.skipped),'tests':EvidenceResult.records,'host':'Windows x64','protocol':V,'tauriWindowExecuted':WINDOW.exists(),'scope':'actual Rust host + C1 executor; MCP/A2A synthetic services; real window separately labeled','paidCalls':0,'accounts':0}
    write(EVIDENCE/'summary.json',summary);write(HERE/'evidence/latest.json',{'directory':str(EVIDENCE.relative_to(HERE)),'summary':summary})
    paths=[*HERE.glob('*.py'),*HERE.glob('host/src/*.rs'),HERE/'host/Cargo.lock',HERE/'host/Cargo.toml',*HERE.glob('host/ui/*'),HERE/'host/tauri.conf.json']
    write(EVIDENCE/'source-hashes.json',{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths if p.is_file()})
    print(json.dumps({'evidence':str(EVIDENCE),**{k:v for k,v in summary.items() if k not in ('tests',)}}))
    if not result.wasSuccessful():print((EVIDENCE/'unittest.log').read_text()[-22000:])
    return 0 if result.wasSuccessful() else 1
if __name__=='__main__':raise SystemExit(main())
