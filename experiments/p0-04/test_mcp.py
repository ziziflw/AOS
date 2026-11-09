"""Distinct evidence for SDK calls, C1 integration, fault servers and static checks."""
import asyncio,json,hashlib,os,sqlite3,subprocess,sys,time,traceback,unittest,importlib.metadata as md
from pathlib import Path
from datetime import datetime,timezone
from copy import deepcopy
from bootstrap import HERE,ROOT,P03,read,write,ContractError,OutcomeError,PROTOCOL
from cases import build,FIX,environment,inputs
from tool_specs import SPECS
from contracts import SchemaClient,Contracts
from integration import Session,MCPRegistry
from mcp_client import MCPClient
from process_host import alive
from mocks import SyntheticSystem
from jsonschema import ValidationError
EVIDENCE=None; V=None

class MCPTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.dir=EVIDENCE/self._testMethodName; self.dir.mkdir(); self.sessions=[]; self.clients=[]; self.checks=[]
    def eq(self,a,b,label):
        self.checks.append({'label':label,'expected':deepcopy(b),'actual':deepcopy(a),'passed':a==b})
        write(self.dir/'assertions.json',self.checks); self.assertEqual(a,b,label)
    def session(self,name='structured_result',mode='normal',label=None,**kw):
        s=Session(self.dir/(label or name+'-'+mode),V,name,mode,**kw); self.sessions.append(s); return s
    async def direct(self,mode='normal',allowed=None,label=None):
        e=environment('echo_text',mode); c=MCPClient(self.dir/(label or 'direct-'+mode),e['extensions']['aos:programs']['program:aos-p04-server'],allowed or list(SPECS))
        self.clients.append(c); await c.open(); return c
    def identity(self,tag='direct'):
        return {'runId':'test-'+self._testMethodName,'nodeKey':'direct/tool','nodeTypeVersion':'0.1.0','attemptId':tag,'attemptNumber':1,'operationId':'op-'+tag}
    async def run_to(self,s): return await asyncio.wait_for(s.runtime.drive(),10)
    async def wait_call(self,s,kind='call-started'):
        for _ in range(1000):
            if any(r['kind']==kind for r in s.ledgers()): return
            await asyncio.sleep(.005)
        self.fail('External server did not reach '+kind)
    def grant(self,s):
        a=next(a for a in s.runtime.snapshot['approvals'].values() if a['status']=='pending')
        s.runtime.approve(a['id'],a['fingerprint']); return a
    def calls(self,s): return [x for x in s.ledgers() if x['kind']=='call-started']
    def effects(self,s): return [x for x in s.ledgers() if x['kind']=='effect-committed']
    async def asyncTearDown(self):
        for s in reversed(self.sessions):
            s.export('assertion-point'); await s.close()
        for c in reversed(self.clients): await c.close()
        pids=[]
        for p in self.dir.rglob('process.jsonl'):
            for line in p.read_text(encoding='utf-8').splitlines():
                r=json.loads(line)
                if r['kind']=='started': pids.append(r['pid'])
        for p in self.dir.rglob('server-ledger.sqlite'):
            db=sqlite3.connect(p)
            try:
                for kind,body in db.execute('SELECT kind,body FROM records'):
                    data=json.loads(body)
                    if kind=='started': pids.append(data['pid'])
                    if kind=='child-started': pids.append(data['childPid'])
            finally: db.close()
        for _ in range(100):
            if not any(alive(pid) for pid in pids): break
            await asyncio.sleep(.01)
        status=[{'pid':pid,'alive':alive(pid)} for pid in sorted(set(pids))]
        write(self.dir/'process-cleanup.json',status)
        self.eq(any(r['alive'] for r in status),False,'no owned experimental server or child remains')

    async def test_T01_real_sdk_discovery_and_calls(self):
        c=await self.direct()
        self.eq(len(c.tools),6,'six discovered tools from independent SDK server')
        init=read(c.dir/'initialize.json'); self.eq(init['protocolVersion'],PROTOCOL,'negotiated fixed protocol')
        self.eq(c.host.p.pid!=os.getpid(),True,'independent operating-system process')
        self.eq(await c.call('echo_text',{'text':'中文 echo'},self.identity('echo')),{'text':'中文 echo'},'UTF-8 real SDK echo')
        self.eq(await c.call('add_numbers',{'a':2.5,'b':3},self.identity('add')),{'sum':5.5},'finite typed numeric output')
        self.eq('Synthetic MCP server pid=' in (c.dir/'stderr.log').read_text(encoding='utf-8'),True,'ordinary log is stderr')

    async def test_T02_parameters_outputs_unknown_and_schema_drift(self):
        c=await self.direct()
        for arguments in ({},{'text':1},{'text':'x','extra':True}):
            with self.assertRaises(ValidationError): await c.call('echo_text',arguments,self.identity('invalid'))
        with self.assertRaises(ValidationError): await c.call('add_numbers',{'a':float('inf'),'b':1},self.identity('infinite'))
        with self.assertRaises(ContractError) as error: await c.call('unknown',{},self.identity('unknown'))
        self.eq(error.exception.code,'TOOL_PERMISSION_DENIED','unknown tool denied before wire call')
        trace=[json.loads(x) for x in (c.dir/'protocol.jsonl').read_text(encoding='utf-8').splitlines()]
        self.eq(sum(x['message'].get('method')=='tools/call' for x in trace),0,'invalid and forbidden calls never sent')
        bad=self.session('echo_text','bad-output'); st=await self.run_to(bad)
        self.eq(st['nodes']['main/tool']['error']['code'],'MCP_OUTPUT_INVALID','SDK rejects malformed structured output')
        self.eq(st['nodes']['main/output']['state'],'skipped','invalid output not forwarded')
        with self.assertRaises(ContractError) as error: await self.direct('schema-drift',allowed=['echo_text'])
        self.eq(error.exception.code,'TOOL_SCHEMA_DRIFT','tool description drift blocks execution')

    async def test_T03_stdout_pollution(self):
        s=self.session('echo_text','stdout-pollution'); st=await self.run_to(s)
        self.eq(st['state'],'failed','read-only protocol corruption is failure')
        self.eq(st['nodes']['main/tool']['error']['code'],'PROTOCOL_STDOUT_CORRUPT','pollution identified explicitly')
        self.eq(st['nodes']['main/tool']['outputs'],{},'pollution cannot become business output')

    async def test_T04_server_abnormal_exit(self):
        s=self.session('echo_text','call-exit'); st=await self.run_to(s)
        self.eq(st['state'],'failed','read-only disconnect fails without fake output')
        self.eq(st['nodes']['main/tool']['error']['code'],'SERVER_DISCONNECTED','disconnect distinguished')
        self.eq(len(st['nodes']['main/tool']['attempts']),1,'no hidden SDK retry')

    async def test_T05_timeout_and_cancellation(self):
        def short(w,r,e):
            w['graph']['nodes'][1]['policy']['timeoutMs']=1500
            r['inputs']['arguments']['delayMs']=1500
        timed=self.session('delayed_result',label='timeout',change=short); st=await self.run_to(timed)
        self.eq(st['nodes']['main/tool']['error']['code'],'MCP_REQUEST_TIMEOUT','adapter deadline distinct from disconnect')
        for mode in ('normal','ignore-cancel'):
            s=self.session('delayed_result',mode,label='cancel-'+mode,
                           change=lambda w,r,e:r['inputs']['arguments'].update(delayMs=500))
            driver=asyncio.create_task(s.runtime.drive()); await self.wait_call(s)
            s.runtime.cancel(); st=await asyncio.wait_for(driver,5)
            self.eq(st['state'],'unknown','cancel notification alone does not confirm physical stop: '+mode)
            self.eq(st['nodes']['main/output']['state'],'cancelled','no continuation after user cancel')
            trace=[json.loads(x) for x in next(s.dir.glob('mcp-*/protocol.jsonl')).read_text(encoding='utf-8').splitlines()]
            self.eq(any(x['message'].get('method')=='notifications/cancelled' for x in trace),True,'real MCP cancellation sent: '+mode)
            if mode=='normal': self.eq(any(x['kind']=='handler-cancelled' for x in s.ledgers()),True,'cooperative handler cancellation observed separately')
            else: self.eq(any(x['kind']=='handler-cancelled' for x in s.ledgers()),False,'ignoring handler is not falsely confirmed cancelled')

    async def test_T06_response_lost_effect_unknown(self):
        s=self.session('simulated_effect','lost-response'); await self.run_to(s); self.grant(s); st=await self.run_to(s)
        self.eq(st['state'],'unknown','external write happened but response lost')
        self.eq(len(self.effects(s)),1,'one isolated ledger effect')
        self.eq(len(self.calls(s)),1,'no automatic second tools/call')
        a=st['nodes']['main/tool']['attempts']; self.eq(len(a),1,'one attempt only')
        self.eq(self.calls(s)[0]['dispatch']['operationId'],st['nodes']['main/tool']['operationId'],'operationId crosses actual protocol')
        self.eq(st['nodes']['main/output']['state'],'skipped','unknown cannot feed downstream')

    async def test_T07_approval_real_mcp_gate(self):
        for action in ('pending','denied','expired','cancelled','changed-content','duplicate'):
            s=self.session('simulated_effect',label=action,ttl=.001 if action=='expired' else 300)
            st=await self.run_to(s); a=next(iter(st['approvals'].values()))
            self.eq(len(s.registry.clients),0,'no external server started before approval: '+action)
            if action=='denied': s.runtime.approve(a['id'],a['fingerprint'],False)
            elif action=='expired':
                await asyncio.sleep(.01)
                with self.assertRaises(ContractError): s.runtime.approve(a['id'],a['fingerprint'])
            elif action=='cancelled':
                s.runtime.cancel()
                with self.assertRaises(ContractError): s.runtime.approve(a['id'],a['fingerprint'])
            elif action=='changed-content':
                changed=self.session('simulated_effect',label='changed-operation',change=lambda w,r,e:r['inputs']['arguments'].update(value='changed'))
                await self.run_to(changed)
                with self.assertRaises(ContractError): changed.runtime.approve(a['id'],a['fingerprint'])
                self.eq(len(changed.registry.clients),0,'old approval cannot dispatch changed operation')
            elif action=='duplicate':
                self.grant(s); self.eq(s.runtime.approve(a['id'],a['fingerprint']),'granted','duplicate submission has no new authority')
                st=await self.run_to(s)
                self.eq(st['state'],'succeeded','valid approval reaches real external SDK server')
                self.eq(len(self.effects(s)),1,'repeated approval yields exactly one observed effect')
                self.eq(len(self.calls(s)),1,'exactly one real MCP tools/call after valid approval')
            self.eq(len(self.effects(s)),1 if action=='duplicate' else 0,'external effect count for '+action)
        expiring=self.session('simulated_effect','slow-init',label='expires-during-handshake',ttl=.4)
        await self.run_to(expiring); self.grant(expiring); st=await self.run_to(expiring)
        self.eq(st['nodes']['main/tool']['error']['code'],'APPROVAL_EXPIRED_BEFORE_MCP','approval rechecked after real handshake')
        self.eq(len(self.calls(expiring)),0,'expired during startup never reaches tools/call')
        self.eq(len(self.effects(expiring)),0,'no write with authorization that expired in startup')

    async def test_T08_original_scenario_b_integration(self):
        s=self.session(); st=await self.run_to(s)
        self.eq(st['state'],'succeeded','scenario B revision executes through C1 and real MCP')
        self.eq(st['scopes']['main']['result']['items'][0]['text'],'查找测试资料','structured result reaches original downstream nodes')
        self.eq([n['state'] for n in st['nodes'].values()],['succeeded']*5,'all five original node roles actually execute')
        self.eq(len(self.calls(s)),1,'one external call in pipeline')
        remote=self.calls(s)[0]['dispatch']; local=st['nodes']['main/tool']
        self.eq(remote['attemptId'],local['attempts'][0]['id'],'attempt identity preserved on wire')
        self.eq(remote['runId'],st['runId'],'same authoritative run identity')
        self.eq(local['outputs']['out']['validity'],'validated','C1 validates downstream envelope')

    async def test_T09_process_tree_init_failure_and_duplicate_close(self):
        c=await self.direct('spawn-child'); await c.call('echo_text',{'text':'tree'},self.identity('tree'))
        await c.close(); await c.close()
        self.eq(alive(c.host.p.pid),False,'direct owned process gone after repeated close')
        with self.assertRaises(ContractError): await self.direct('init-exit',label='init-exit')
        with self.assertRaises(ContractError): await self.direct('bad-version',label='bad-version')
        self.eq(True,True,'initialization failures surfaced and resources subsequently audited')

    async def test_T10_owner_process_crash_recovery(self):
        for mode in ('before-call','during-call','after-call'):
            s=self.session('simulated_effect' if mode=='during-call' else 'echo_text','effect-delay' if mode=='during-call' else 'normal',label=mode)
            if mode=='during-call': await self.run_to(s); self.grant(s)
            directory=s.dir; rid=s.runtime.snapshot['runId']; await s.close(); self.sessions.remove(s)
            proc=await asyncio.to_thread(subprocess.run,[sys.executable,'-B','-X','utf8',str(HERE/'crash_worker.py'),str(directory),mode],
                                        capture_output=True,text=True,encoding='utf-8',timeout=20,creationflags=subprocess.CREATE_NO_WINDOW)
            write(directory/'worker-result.json',{'returnCode':proc.returncode,'stdout':proc.stdout,'stderr':proc.stderr})
            self.eq(proc.returncode,74,'actual owning process exited at '+mode)
            db=sqlite3.connect(directory/'run.sqlite')
            persisted=json.loads(db.execute('SELECT state FROM snapshot').fetchone()[0]); db.close(); write(directory/'persisted-before-recovery.json',persisted)
            q=Session(directory,V,recover=True); self.sessions.append(q); st=await self.run_to(q)
            self.eq(st['runId'],rid,'same run recovered at '+mode)
            self.eq(st['state'],'unknown' if mode=='during-call' else 'succeeded','correct committed/unconfirmed interpretation at '+mode)
            self.eq(len(self.effects(q)),1 if mode=='during-call' else 0,'no replay of external write at '+mode)
            self.eq(len(self.calls(q)),1,'each operation dispatched at most once at '+mode)

    async def test_T11_safe_retry_owned_by_C1(self):
        def change(w,r,e):
            w['graph']['nodes'][1]['policy'].update(maxAttempts=2,retryMode='safe')
            r['inputs']['arguments']['mode']='retry-once'
        s=self.session('simulated_failure',change=change); st=await self.run_to(s)
        self.eq(st['state'],'succeeded','trusted pure transient error retried by C1')
        self.eq([a['state'] for a in st['nodes']['main/tool']['attempts']],['failed','succeeded'],'distinct failed/success attempts')
        calls=self.calls(s); self.eq(len(calls),2,'exactly two actual SDK calls')
        self.eq(len({x['dispatch']['operationId'] for x in calls}),1,'stable logical operation over attempts')
        self.eq(len({x['dispatch']['attemptId'] for x in calls}),2,'different actual attempt identifiers')

    async def test_T12_definition_environment_and_permission_diagnostics(self):
        from common import check_references
        schema={'type':'object','properties':{'resourceUri':{'type':'string'}}}
        check_references(schema,schema=True)
        with self.assertRaises(ContractError): check_references({'resourceUri':'workspace:source/../escape'})
        self.eq(True,True,'schema property declaration distinguished from actual traversal value')
        w,r=inputs('structured_result'); e=environment('structured_result')
        self.eq('D:\\' in json.dumps(w),False,'portable workflow contains no Windows drive path')
        self.eq(e['connections']['connection:p04']['programRef'],'program:aos-p04-server','launch reference belongs to EnvironmentBinding')
        def missing(w,r,e): e['extensions']['aos:programs']['program:aos-p04-server']['executable']='D:/AIOrchestrationStudio/experiments/p0-04/absent.exe'
        with self.assertRaises(ContractError) as error: self.session(change=missing,label='missing-server')
        self.eq(error.exception.code,'SERVER_PROGRAM_MISSING','missing server blocks execution')
        self.eq(read(self.dir/'missing-server/workflow.json'),w,'definition remains openable without server; no GUI claim')
        e['platform']['os']='linux'; e['extensions']['aos:programs']['program:aos-p04-server']['executable']='/opt/aos/python'
        V.validate(e); write(self.dir/'linux-binding-static-only.json',e)
        self.eq(True,True,'replacement binding structurally valid; no Linux execution claimed')
        with self.assertRaises(ContractError) as error:
            self.session(label='permission-denied',change=lambda w,r,e:e['extensions'].update({'aos:allowed-tools':[]}))
        self.eq(error.exception.code,'TOOL_PERMISSION_DENIED','server tool advertisement grants no permission')
        bad_w=deepcopy(w); bad_w['graph']['nodes'][2]['typeId']='tool.mcp.unknown'
        system=SyntheticSystem(self.dir/'diagnostic.sqlite')
        try:
            with self.assertRaises(ContractError) as error: Contracts(bad_w,r,FIX/'catalog.json',V,MCPRegistry(system,self.dir,e))
            self.eq(error.exception.code,'NODE_UNRESOLVED','unsupported tool node diagnosed during load')
        finally: system.close()

    async def test_T13_local_persistence_failure_fails_closed(self):
        injected=False
        def hook(stage,event):
            nonlocal injected
            if not injected and stage=='before_commit' and event.get('key')=='main/tool' and event['kind']=='node-terminal':
                injected=True; raise OSError('Synthetic storage write failure')
        s=self.session('simulated_effect',hook=hook); await self.run_to(s); self.grant(s)
        with self.assertRaises(OutcomeError) as error: await self.run_to(s)
        self.eq(error.exception.code,'LOCAL_PERSISTENCE_FAILURE','storage failure fences controller')
        self.eq(s.store.load()['nodes']['main/tool']['state'],'running','no fabricated durable success after failed commit')
        self.eq(len(self.effects(s)),1,'external ledger remains committed independently')
        directory=s.dir; s.export('storage-failed'); await s.close(); self.sessions.remove(s)
        q=Session(directory,V,recover=True); self.sessions.append(q); st=await self.run_to(q)
        self.eq(st['state'],'unknown','restart interprets unconfirmed result conservatively')
        self.eq(len(self.effects(q)),1,'no replay after storage failure')

    async def test_T14_tool_errors_and_jsonrpc_errors(self):
        for mode,code in (('tool-error','MCP_TOOL_ERROR'),('protocol-error','MCP_JSONRPC_ERROR')):
            s=self.session('simulated_failure',label=mode,change=lambda w,r,e,mode=mode:r['inputs']['arguments'].update(mode=mode))
            st=await self.run_to(s)
            self.eq(st['nodes']['main/tool']['error']['code'],code,'distinct error mapping '+mode)
            self.eq(st['state'],'failed','explicit non-writing tool failure '+mode)

class EvidenceResult(unittest.TextTestResult):
    records=[]
    def addSuccess(self,test): self.records.append({'test':test.id(),'status':'passed'});super().addSuccess(test)
    def addFailure(self,test,err): self.records.append({'test':test.id(),'status':'failed','traceback':''.join(traceback.format_exception(*err))});super().addFailure(test,err)
    def addError(self,test,err): self.records.append({'test':test.id(),'status':'error','traceback':''.join(traceback.format_exception(*err))});super().addError(test,err)
def main():
    global EVIDENCE,V
    build(); EVIDENCE=HERE/'evidence'/('suite-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')); EVIDENCE.mkdir(parents=True)
    V=SchemaClient(ROOT/'research/02-node-contracts/schemas/contract.schema.json',FIX/'catalog.json')
    with (EVIDENCE/'unittest.log').open('w',encoding='utf-8') as log:
        try: result=unittest.TextTestRunner(stream=log,verbosity=2,resultclass=EvidenceResult).run(unittest.defaultTestLoader.loadTestsFromTestCase(MCPTests))
        finally: V.close()
    manifest={'testsRun':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'tests':EvidenceResult.records,
              'protocol':PROTOCOL,'clientSDK':md.version('mcp'),'serverSDK':md.version('mcp'),'python':sys.version,'host':sys.platform,
              'scope':'real official SDK stdio calls to independent trusted synthetic processes; static diagnostics distinguished by test',
              'paidModelCalls':0,'realAccounts':0,'LinuxRuns':0,'macOSRuns':0}
    write(EVIDENCE/'summary.json',manifest); write(HERE/'evidence/latest.json',{'directory':EVIDENCE.relative_to(HERE).as_posix(),'summary':manifest})
    paths=[*HERE.glob('*.py'),*P03.glob('*.py'),P03/'schema_host.ps1',*FIX.glob('*.json')]
    write(EVIDENCE/'source-hashes.json',{p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})
    print(json.dumps({'evidence':str(EVIDENCE),'testsRun':result.testsRun,'failures':len(result.failures),'errors':len(result.errors)}))
    if not result.wasSuccessful(): print((EVIDENCE/'unittest.log').read_text(encoding='utf-8')[-24000:])
    return 0 if result.wasSuccessful() else 1
if __name__=='__main__': raise SystemExit(main())
