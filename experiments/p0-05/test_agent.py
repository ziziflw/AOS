"""Actual A2A, synthetic Agent semantics, C1 integration and static diagnostics are labeled."""
import asyncio,hashlib,json,os,sqlite3,subprocess,sys,time,traceback,unittest,importlib.metadata as md
from pathlib import Path
from datetime import datetime,timezone
from copy import deepcopy
from bootstrap_agent import HERE,ROOT,P03,P04,SECRET,WIRE,SPEC,read,write,ContractError,OutcomeError
from agent_cases import build,FIX,args
from agent_integration import Session
from agent_client import AgentClient
from service_host import ServiceHost,alive
from contracts import SchemaClient
from a2a.utils.errors import InvalidParamsError,A2AError
EVIDENCE=None;V=None
class AgentTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.dir=EVIDENCE/self._testMethodName;self.dir.mkdir();self.hosts={};self.sessions=[];self.clients=[];self.checks=[]
    def eq(self,actual,expected,label):
        self.checks.append({'label':label,'expected':deepcopy(expected),'actual':deepcopy(actual),'passed':actual==expected})
        write(self.dir/'assertions.json',self.checks);self.assertEqual(actual,expected,label)
    async def hosts_ready(self,parallel=False,bad_card=False):
        for name in (('agentA','agentB') if parallel else ('agentA',)):
            if name not in self.hosts:self.hosts[name]=await ServiceHost(self.dir/name,name,bad_card).start()
        return self.hosts
    async def session(self,label='run',**kw):
        await self.hosts_ready(kw.get('parallel',False));s=Session(self.dir/label,V,self.hosts,**kw);self.sessions.append(s);return s
    async def direct(self,name='agentA'):
        await self.hosts_ready(name=='agentB');c=AgentClient(self.dir/('direct-'+str(len(self.clients))),self.hosts[name].endpoint,name)
        self.clients.append(c);await c.open();return c
    def local_identity(self,tag='direct'):return {'runId':'test-'+self._testMethodName,'nodeKey':tag,'nodeTypeVersion':'0.1.0','attemptId':'attempt-'+tag,'attemptNumber':1,'operationId':'op-'+tag,'workflowRevision':'r1','skill':'echo'}
    def records(self,name='agentA'):
        db=sqlite3.connect(self.hosts[name].dir/'agent.sqlite')
        try:return [{'seq':r[0],'kind':r[1],**json.loads(r[2])} for r in db.execute('SELECT * FROM events ORDER BY seq')]
        finally:db.close()
    def tasks(self,name='agentA'):
        db=sqlite3.connect(self.hosts[name].dir/'agent.sqlite')
        try:return [json.loads(x[0]) for x in db.execute('SELECT body FROM tasks ORDER BY id')]
        finally:db.close()
    def effects(self):
        db=sqlite3.connect(self.hosts['agentA'].dir/'agent.sqlite')
        try:return db.execute('SELECT * FROM effects').fetchall()
        finally:db.close()
    async def run_to(self,s):return await asyncio.wait_for(s.runtime.drive(),12)
    def grant(self,s):
        a=next(a for a in s.runtime.snapshot['approvals'].values() if a['status']=='pending');s.runtime.approve(a['id'],a['fingerprint']);return a
    async def wait_external(self,s,phase=None):
        for _ in range(1000):
            nodes=s.runtime.snapshot['nodes'].values()
            if phase:
                if any(n.get('phase')==phase for n in nodes):return
            elif any(n.get('external',{}).get('taskId') for n in nodes):return
            await asyncio.sleep(.005)
        self.fail('Expected external task or phase not reached')
    async def wait_remote_terminal(self,name='agentA'):
        for _ in range(700):
            ts=self.tasks(name)
            if ts and all(t['status']['state'] in ('TASK_STATE_COMPLETED','TASK_STATE_CANCELED','TASK_STATE_REJECTED','TASK_STATE_FAILED') for t in ts):return
            await asyncio.sleep(.005)
        self.fail('Remote task did not settle')
    async def crashed_run(self,label='crash',delay=2200):
        s=await self.session(label,delay=delay,timeout=6000);rid=s.runtime.snapshot['runId'];directory=s.dir
        await s.close();self.sessions.remove(s)
        proc=await asyncio.to_thread(subprocess.run,[sys.executable,'-B','-X','utf8',str(HERE/'crash_engine.py'),str(directory)],
            capture_output=True,text=True,encoding='utf-8',timeout=20,creationflags=subprocess.CREATE_NO_WINDOW)
        write(directory/'worker-result.json',{'returnCode':proc.returncode,'stdout':proc.stdout,'stderr':proc.stderr})
        self.eq(proc.returncode,85,'actual workflow owning process terminated after task identity committed')
        db=sqlite3.connect(directory/'run.sqlite')
        try:persisted=json.loads(db.execute('SELECT state FROM snapshot').fetchone()[0])
        finally:db.close()
        write(directory/'persisted-before-recovery.json',persisted);return directory,rid,persisted
    async def asyncTearDown(self):
        for s in reversed(self.sessions):s.export('assertion-point');await s.close()
        for c in self.clients:await c.close()
        for host in self.hosts.values():
            write(host.dir/'observed-events.json',self.records(host.name));write(host.dir/'observed-tasks.json',self.tasks(host.name))
            await host.close()
        pids=sorted({pid for h in self.hosts.values() for pid in h.pids})
        for _ in range(100):
            if not any(alive(pid) for pid in pids):break
            await asyncio.sleep(.01)
        rows=[{'pid':pid,'alive':alive(pid)} for pid in pids];write(self.dir/'process-cleanup.json',rows)
        self.eq(any(x['alive'] for x in rows),False,'all owned Agent service processes cleaned up')

    async def test_T01_normal_delegation_pipeline(self):
        s=await self.session();st=await self.run_to(s)
        self.eq(st['state'],'succeeded','submit query completion artifact and downstream succeed')
        out=st['scopes']['main']['result'];self.eq(out['text'],'SYNTHETIC','structured deterministic output')
        ext=st['nodes']['main/agent']['external'];self.eq(out['taskId'],ext['taskId'],'taskId bound to output')
        self.eq(len(self.tasks()),1,'one independently accepted remote task')
        self.eq(st['nodes']['main/agent']['outputs']['out']['validity'],'validated','C1 validates final envelope')
        self.eq(any(r['kind']=='agent-artifact-validated' for r in s.store.events()),True,'artifact actually fetched and checked')

    async def test_T02_asynchronous_states_and_progress(self):
        s=await self.session(delay=700);driver=asyncio.create_task(s.runtime.drive());await self.wait_external(s)
        mid=s.runtime.snapshot;ext=mid['nodes']['main/agent']['external']
        self.eq(mid['nodes']['main/agent']['state'],'running','local node remains running after taskId arrives')
        self.eq(ext['remoteState'] in ('TASK_STATE_SUBMITTED','TASK_STATE_WORKING'),True,'submission returns before completion')
        self.eq(mid['nodes']['main/output']['state'],'queued','downstream waits for validated completed output')
        st=await asyncio.wait_for(driver,8)
        progress=[e['progress'] for e in s.store.events() if e['kind']=='agent-observed']
        self.eq(10 in progress and 60 in progress and 100 in progress,True,'real queried progress persisted')
        self.eq(st['state'],'succeeded','asynchronous query pipeline settles')

    async def test_T03_remote_rejection(self):
        s=await self.session(mode='reject');st=await self.run_to(s)
        self.eq(st['state'],'failed','rejection is explicit local failure')
        self.eq(st['nodes']['main/agent']['external']['remoteState'],'TASK_STATE_REJECTED','original rejected state retained')
        self.eq(st['nodes']['main/agent']['error']['code'],'AGENT_REJECTED','rejection reason distinct')
        self.eq(st['nodes']['main/output']['state'],'skipped','no manufactured result')

    async def test_T04_real_disconnect_requery_same_task(self):
        s=await self.session(mode='query-drop-once',delay=600);st=await self.run_to(s)
        self.eq(st['state'],'succeeded','real truncated HTTP connection recovered by query')
        self.eq(sum(e['kind']=='task-created' for e in self.records()),1,'no second SendMessage after lost query response')
        self.eq(any(e['kind']=='wire-response-dropped' and e['method']=='GetTask' for e in self.records()),True,'actual query connection drop injected')
        queried={e['taskId'] for e in self.records() if e['kind']=='get-task'}
        self.eq(sorted(queried),[st['nodes']['main/agent']['external']['taskId']],'all queries refer to one stable task')

    async def test_T05_submission_response_lost_unknown_and_reconcile(self):
        s=await self.session('unverifiable',mode='lost-submit');st=await self.run_to(s)
        self.eq(st['state'],'unknown','request accepted but taskId response lost is not ordinary failure')
        self.eq(st['nodes']['main/agent']['external']['taskId'],None,'no taskId invented')
        self.eq(len(self.tasks()),1,'server created one task despite client timeout')
        self.eq(st['nodes']['main/output']['state'],'skipped','unknown submission cannot advance')
        q=await self.session('reconcile',mode='lost-submit',reconcile=True);result=await self.run_to(q)
        self.eq(result['state'],'succeeded','opt-in profile reconciles via standard ListTasks and exact metadata')
        self.eq(len(self.tasks()),2,'one task per distinct run, no blind resubmit')
        self.eq(any(e['kind']=='agent-submission-reconciled' for e in q.store.events()),True,'reconciliation is explicit and recorded')
        effect=await self.session('unknown-effect',mode='lost-submit',skill='effect');await self.run_to(effect);self.grant(effect);st=await self.run_to(effect)
        self.eq(st['state'],'unknown','lost controlled submission never gets a blind second submit')
        await self.wait_remote_terminal()
        self.eq(len(self.effects()),1,'unknown accepted task may independently commit one synthetic effect')
        self.eq(len(self.tasks()),3,'three distinct logical runs each created only one task')

    async def test_T06_cancel_confirmed_unsupported_and_completion_race(self):
        for mode,expected in (('normal','cancelled'),('cancel-unsupported','unknown'),('finish-after-cancel','unknown')):
            s=await self.session(mode,mode=mode,delay=600);driver=asyncio.create_task(s.runtime.drive());await self.wait_external(s)
            s.runtime.cancel();st=await asyncio.wait_for(driver,6)
            self.eq(st['state'],expected,'local cancellation state for '+mode)
            ext=st['nodes']['main/agent']['external'];remote=next(t for t in self.tasks() if t['id']==ext['taskId'])
            self.eq(any(e['kind']=='cancel-received' and e['taskId']==ext['taskId'] for e in self.records()),True,'Agent actually receives cancellation '+mode)
            if expected=='cancelled':self.eq(remote['status']['state'],'TASK_STATE_CANCELED','confirmed remote terminal, not button state')
            else:
                await self.wait_remote_terminal();remote=next(t for t in self.tasks() if t['id']==ext['taskId'])
                self.eq(remote['status']['state'],'TASK_STATE_COMPLETED','non-cancelable task independently completes')
                self.eq(s.runtime.snapshot['nodes']['main/agent']['outputs'],{},'late remote completion not published')

    async def test_T07_two_independent_agents_parallel_join(self):
        s=await self.session(parallel=True,delay=900);st=await self.run_to(s)
        self.eq(st['state'],'succeeded','two actual Agent services join successfully')
        out=st['scopes']['main']['result'];self.eq([r['agent'] for r in out],['agentA','agentB'],'edge order and Agent source preserved')
        self.eq(len({r['taskId'] for r in out}),2,'different external task IDs')
        self.eq(len({r['artifact']['resourceUri'] for r in out}),2,'no shared artifact references')
        intervals=[]
        for name in ('agentA','agentB'):
            events=self.records(name);start=min(e['time'] for e in events if e['kind']=='task-state' and e['state']=='TASK_STATE_WORKING');end=max(e['time'] for e in events if e['kind']=='task-state' and e['state']=='TASK_STATE_COMPLETED');intervals.append((start,end))
        self.eq(max(x[0] for x in intervals)<min(x[1] for x in intervals),True,'independent service execution intervals overlap')
        self.eq(len({h.pids[-1] for h in self.hosts.values()}),2,'two separate OS processes, not imported functions')

    async def test_T08_engine_crash_query_only_recovery(self):
        directory,rid,before=await self.crashed_run();old=before['nodes']['main/agent'];self.eq(alive(self.hosts['agentA'].pids[-1]),True,'Agent remains alive after engine exits')
        q=Session(directory,V,recover=True);self.sessions.append(q);st=await self.run_to(q)
        self.eq(st['state'],'succeeded','recovered C1 queries existing task to completion')
        self.eq(st['runId'],rid,'same workflow run')
        n=st['nodes']['main/agent'];self.eq(n['attempts'][0]['id'],old['attempts'][0]['id'],'same NodeAttempt, not a new submit attempt')
        self.eq(n['external']['taskId'],old['external']['taskId'],'same external task')
        self.eq(n['operationId'],old['operationId'],'same logical operation')
        self.eq(n['external']['deadlineEpoch'],old['external']['deadlineEpoch'],'restart does not renew the remote waiting deadline')
        self.eq(len(n['attempts']),1,'query recovery does not append attempt')
        self.eq(len(self.tasks()),1,'one remote task after executor restart')
        self.eq(any(e['kind']=='agent-query-resumed' for e in q.store.events()),True,'query-only recovery is audited')

    async def test_T09_stale_definition_and_authorization_results(self):
        s=await self.session('old');await self.run_to(s);directory=s.dir;original=read(directory/'request.json');await s.close();self.sessions.remove(s)
        changed=deepcopy(original);changed['inputs']['arguments']['text']='new-input';write(directory/'request.json',changed)
        with self.assertRaises(ContractError) as error:Session(directory,V,recover=True)
        self.eq(error.exception.code,'RECOVERY_DEFINITION_MISMATCH','changed inputs cannot reuse an old run result');write(directory/'request.json',original)
        fresh=await self.session('new',change=lambda w,r,e:r['inputs']['arguments'].update(text='new-input'));st=await self.run_to(fresh)
        self.eq(st['scopes']['main']['result']['text'],'NEW-INPUT','fresh run does not borrow old task output')
        exp=await self.session('expired',skill='effect',delay=1000,ttl=.35);await self.run_to(exp);self.grant(exp);st=await self.run_to(exp)
        self.eq(st['state'],'unknown','authorization expired before publication blocks old result')
        self.eq(len(self.effects()),1,'already accepted remote effect cannot be retroactively undone by local expiry')
        self.eq(st['nodes']['main/output']['state'],'skipped','expired output never drives downstream')

    async def test_T10_artifact_schema_source_and_availability(self):
        for mode,expected in (('bad-result','failed'),('bad-reference','failed'),('result-delayed','succeeded'),('result-never','unknown')):
            s=await self.session(mode,mode=mode,delay=200,timeout=1100);st=await self.run_to(s)
            self.eq(st['state'],expected,'artifact handling '+mode)
            self.eq(st['nodes']['main/agent']['external']['remoteState'],'TASK_STATE_COMPLETED','remote completed retained separately '+mode)
            if mode.startswith('bad-'):
                self.eq(st['nodes']['main/agent']['error']['code'],'AGENT_ARTIFACT_INVALID','invalid result/reference isolated')
                self.eq(list((s.dir/'artifacts').glob('*')) if (s.dir/'artifacts').exists() else [],[],'no file read or materialization from untrusted reference')
            if mode=='result-never':self.eq(st['nodes']['main/agent']['error']['code'],'AGENT_RESULT_UNAVAILABLE','completed-but-missing result is unknown, not failed')

    async def test_T11_approval_controls_real_send_message(self):
        for action in ('pending','denied','expired','cancelled','duplicate'):
            s=await self.session(action,skill='effect',ttl=.001 if action=='expired' else 300);st=await self.run_to(s);a=next(iter(st['approvals'].values()))
            before=len(self.tasks());self.eq(len(s.registry.clients),0,'no protected protocol request before approval '+action)
            if action=='denied':s.runtime.approve(a['id'],a['fingerprint'],False);await self.run_to(s)
            elif action=='expired':
                await asyncio.sleep(.01)
                with self.assertRaises(ContractError):s.runtime.approve(a['id'],a['fingerprint'])
            elif action=='cancelled':
                s.runtime.cancel()
                with self.assertRaises(ContractError):s.runtime.approve(a['id'],a['fingerprint'])
                await self.run_to(s)
            elif action=='duplicate':
                self.grant(s);self.eq(s.runtime.approve(a['id'],a['fingerprint']),'granted','duplicate approval grants no second submit');st=await self.run_to(s)
                self.eq(st['state'],'succeeded','approved controlled task uses real A2A')
            self.eq(len(self.tasks())-before,1 if action=='duplicate' else 0,'accepted remote task count '+action)
        self.eq(len(self.effects()),1,'only valid approved task writes synthetic effect ledger')

    async def test_T12_abnormal_states_timeout_exit_and_protocol_error(self):
        for mode in ('fail','wait-input','wait-auth','query-unavailable','protocol-error','service-exit'):
            s=await self.session(mode,mode=mode,delay=250,timeout=600)
            if mode in ('wait-input','wait-auth'):
                driver=asyncio.create_task(s.runtime.drive());phase='waiting-agent-input' if mode=='wait-input' else 'waiting-agent-auth';await self.wait_external(s,phase)
                self.eq(s.runtime.snapshot['nodes']['main/agent']['state'],'running','waiting state not flattened into failure '+mode)
                s.runtime.cancel();st=await asyncio.wait_for(driver,5);self.eq(st['state'],'cancelled','waiting remote task can acknowledge cancellation '+mode)
            else:
                st=await self.run_to(s);self.eq(st['state'],'failed' if mode=='fail' else 'unknown','distinct abnormal semantics '+mode)
            if mode=='service-exit':self.eq(alive(self.hosts['agentA'].pids[-1]),False,'actual Agent process exited')
        # New service for actual deadline case, retaining the same isolated task database.
        await self.hosts['agentA'].stop();await self.hosts['agentA'].start()
        timed=await self.session('timeout',delay=2000,timeout=300);st=await self.run_to(timed)
        self.eq(st['nodes']['main/agent']['error']['code'],'AGENT_WAIT_TIMEOUT','bounded wait without pretending remote task failed')

    async def test_T13_task_identity_mismatch(self):
        for mode,code in (('wrong-identity','AGENT_IDENTITY_MISMATCH'),('wrong-task','AGENT_TASK_ID_MISMATCH')):
            s=await self.session(mode,mode=mode);st=await self.run_to(s)
            self.eq(st['state'],'unknown','untrusted task identity cannot become local success')
            self.eq(st['nodes']['main/agent']['error']['code'],code,'identity mismatch diagnosed')
            self.eq(st['nodes']['main/agent']['outputs'],{},'mismatched source never published')

    async def test_T14_duplicate_submission_and_duplicate_result(self):
        c=await self.direct();local=self.local_identity('dedup');arguments=args('duplicate',delay=300)
        a=await c.send(arguments,local,'stable-message','context-dedup');b=await c.send(arguments,local,'stable-message','context-dedup')
        self.eq(a['id'],b['id'],'server messageId dedup returns stable taskId')
        self.eq(len(self.tasks()),1,'no second task from exact duplicate submission')
        with self.assertRaises(A2AError):await c.send(args('changed'),local,'stable-message','context-dedup')
        self.eq(len(self.tasks()),1,'same messageId with changed content is rejected')
        s=await self.session('workflow',mode='duplicate');st=await self.run_to(s);tid=st['nodes']['main/agent']['external']['taskId']
        one=await c.query(tid);two=await c.query(tid);self.eq(one,two,'duplicate completed result via actual GetTask')
        self.eq(s.runtime.observation('main/agent',two),False,'terminal C1 rejects late duplicate observation')
        self.eq(len(st['nodes']['main/output']['attempts']),1,'downstream executes once')

    async def test_T15_old_state_cannot_overwrite_new(self):
        s=await self.session(mode='stale-state');st=await self.run_to(s)
        self.eq(st['nodes']['main/agent']['error']['code'],'AGENT_STATE_REGRESSION','stale remote sequence rejected')
        self.eq(st['nodes']['main/agent']['external']['remoteState'],'TASK_STATE_WORKING','accepted state not overwritten by old submitted')
        self.eq(st['nodes']['main/agent']['external']['lastSequence']>=2,True,'accepted sequence remains monotonic')

    async def test_T16_invalid_parameters_versions_and_missing_service(self):
        await self.hosts_ready()
        with self.assertRaises(ContractError):await self.session('invalid',change=lambda w,r,e:r['inputs']['arguments'].update(delayMs='not-int'))
        self.eq(len(self.tasks()),0,'invalid typed input causes no task creation')
        c=await self.direct()
        with self.assertRaises(A2AError):await c.send({'text':'bad'},self.local_identity(),'invalid-message','context-invalid')
        self.eq(len(self.tasks()),0,'server SDK rejects invalid parameters independently')
        c.http.headers['A2A-Version']='9.9'
        with self.assertRaises(A2AError):await c.send(args(),self.local_identity(),'bad-version','context-version')
        self.eq(len(self.tasks()),0,'unsupported protocol version never starts a task')
        with self.assertRaises(ContractError) as error:
            await self.session('retry',change=lambda w,r,e:w['graph']['nodes'][1]['policy'].update(maxAttempts=2,retryMode='safe'))
        self.eq(error.exception.code,'AGENT_RETRY_UNSUPPORTED','node retries cannot create independent remote tasks')
        await self.hosts['agentA'].stop()
        missing=await self.session('missing');st=await self.run_to(missing)
        self.eq(st['state'],'failed','missing Agent discovery blocks execution')
        self.eq(len(read(missing.dir/'workflow.json')['graph']['nodes']),3,'unavailable service does not delete node definition')
        self.hosts['agentB']=await ServiceHost(self.dir/'agentB','agentB',bad_card=True).start()
        bad=AgentClient(self.dir/'bad-card',self.hosts['agentB'].endpoint,'agentB');self.clients.append(bad)
        with self.assertRaises(ContractError) as error:await bad.open()
        self.eq(error.exception.code,'AGENT_CAPABILITY_DRIFT','changed Agent Card version blocks task submission')

    async def test_T17_sensitive_error_redaction(self):
        s=await self.session(mode='bad-secret-error');st=await self.run_to(s)
        self.eq(st['state'],'unknown','server diagnostic error leaves unverified task unknown')
        texts=[]
        for path in self.dir.rglob('*'):
            if path.is_file() and path.suffix in ('.json','.jsonl','.log'):texts.append(path.read_text(encoding='utf-8',errors='replace'))
        self.eq(any(SECRET in text for text in texts),False,'synthetic bearer/error marker absent from saved logs')
        self.eq(any('[REDACTED]' in text for text in texts),True,'redaction actually applied to protocol evidence')

    async def test_T18_service_persistence_and_query_recovery(self):
        directory,rid,before=await self.crashed_run('persist',delay=2000);host=self.hosts['agentA'];endpoint=host.endpoint;old_pid=host.pids[-1]
        await host.stop();await host.start()
        self.eq(host.endpoint,endpoint,'same environment binding restored after service restart')
        self.eq(host.pids[-1]!=old_pid,True,'actual new independent Agent service process')
        q=Session(directory,V,recover=True);self.sessions.append(q);st=await self.run_to(q)
        self.eq(st['state'],'succeeded','persisted task resumes in Agent then C1 queries it')
        self.eq(st['nodes']['main/agent']['external']['taskId'],before['nodes']['main/agent']['external']['taskId'],'stable persisted task ID')
        self.eq(len(self.tasks()),1,'service restart and engine recovery never resubmit')

class EvidenceResult(unittest.TextTestResult):
    records=[]
    def addSuccess(self,test):self.records.append({'test':test.id(),'status':'passed'});super().addSuccess(test)
    def addFailure(self,test,err):self.records.append({'test':test.id(),'status':'failed','traceback':''.join(traceback.format_exception(*err))});super().addFailure(test,err)
    def addError(self,test,err):self.records.append({'test':test.id(),'status':'error','traceback':''.join(traceback.format_exception(*err))});super().addError(test,err)
def main():
    global EVIDENCE,V
    build();EVIDENCE=HERE/'evidence'/('suite-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));EVIDENCE.mkdir(parents=True)
    V=SchemaClient(ROOT/'research/02-node-contracts/schemas/contract.schema.json',FIX/'catalog.json')
    with (EVIDENCE/'unittest.log').open('w',encoding='utf-8') as log:
        try:result=unittest.TextTestRunner(stream=log,verbosity=2,resultclass=EvidenceResult).run(unittest.defaultTestLoader.loadTestsFromTestCase(AgentTests))
        finally:V.close()
    manifest={'testsRun':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'tests':EvidenceResult.records,'specification':SPEC,'wireVersion':WIRE,
        'clientSDK':md.version('a2a-sdk'),'serverSDK':md.version('a2a-sdk'),'python':sys.version,'host':sys.platform,
        'scope':'real official A2A JSON-RPC to independent synthetic Agent services, C1 integration and explicitly labeled static diagnostics',
        'paidModelCalls':0,'realAccounts':0,'LinuxRuns':0,'macOSRuns':0}
    write(EVIDENCE/'summary.json',manifest);write(HERE/'evidence/latest.json',{'directory':EVIDENCE.relative_to(HERE).as_posix(),'summary':manifest})
    paths=[*HERE.glob('*.py'),*P03.glob('*.py'),*P04.glob('*.py'),P03/'schema_host.ps1',*FIX.glob('*.json')]
    write(EVIDENCE/'source-hashes.json',{p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})
    print(json.dumps({'evidence':str(EVIDENCE),'testsRun':result.testsRun,'failures':len(result.failures),'errors':len(result.errors)}))
    if not result.wasSuccessful():print((EVIDENCE/'unittest.log').read_text(encoding='utf-8')[-28000:])
    return 0 if result.wasSuccessful() else 1
if __name__=='__main__':raise SystemExit(main())
