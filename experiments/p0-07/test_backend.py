"""Independent Rust probe tests for the editable-definition API and original C1."""
import asyncio,hashlib,importlib.util,json,sqlite3,time,unittest,traceback
from pathlib import Path
from datetime import datetime,timezone
from copy import deepcopy
from boot import HERE,ROOT,read,write,digest,ContractError
from workbench_profile import sample,CATALOG
spec=importlib.util.spec_from_file_location('p006_tests',HERE.parent/'p0-06/test_host.py')
old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
old.HERE=HERE;old.HOST=HERE/'host/target/debug/host-probe.exe'
EVIDENCE=None
class BackendTests(unittest.TestCase):
    def setUp(self):
        self.dir=EVIDENCE/self._testMethodName;self.dir.mkdir();self.d=old.Driver(self.dir/'session');self.d.start();self.checks=[]
    def tearDown(self):self.d.close();write(self.dir/'assertions.json',self.checks)
    def eq(self,a,b,label):self.checks.append({'label':label,'expected':b,'actual':a,'passed':a==b});self.assertEqual(a,b,label)
    def prepare(self,w):return self.d.good('load',{'action':'validate','workflow':w})
    def start(self,w):p=self.prepare(w);return self.d.good('create',{'token':p['token']})
    def test_T01_editable_real_mcp(self):
        w=sample()['workflow'];w['graph']['nodes'][0]['config']['value']='后端编辑'
        self.start(w);s=self.d.wait();self.eq(s['state'],'succeeded','actual C1 terminal')
        self.eq(s['nodes']['main/output']['result'],'合成回答：后端编辑 / 已整理','actual typed output')
        self.eq(s['identity']['workflow'],digest(w),'pinned definition')
        latest=read(self.d.dir/'latest.json');ledger=list((self.d.dir/'runs'/latest['key']).glob('mcp-*/server-ledger.sqlite'))
        self.eq(len(ledger),1,'actual independent MCP ledger')
        db=sqlite3.connect(self.d.dir/'runs'/latest['key']/'run.sqlite')
        stored=json.loads(db.execute('SELECT state FROM snapshot WHERE id=1').fetchone()[0]);db.close()
        self.eq(s,stored,'exact numeric and state roundtrip vs independent SQLite')
    def test_T02_backend_type_and_schema_rejection(self):
        w=sample()['workflow'];w['graph']['edges'][0]['to']={'node':'tool','port':'args'}
        self.eq(self.d.call('load',{'action':'validate','workflow':w})['error']['code'],'PORT_TYPE_MISMATCH','Text to MCP JSON blocked')
        w=sample()['workflow'];w['graph']['nodes'][2]['config']['temperature']=4
        self.eq(self.d.call('load',{'action':'validate','workflow':w})['error']['code'],'CONFIG_INVALID','number range enforced')
        w=sample()['workflow'];w['graph']['nodes'][2]['typeVersion']='9.0.0'
        self.eq(self.d.call('load',{'action':'validate','workflow':w})['error']['code'],'NODE_UNRESOLVED','version drift blocked')
    def test_T03_unknown_lossless_and_paths(self):
        doc=sample();doc['workflow']['graph']['nodes'][0]['typeId']='future.unknown';doc['workflow']['extensions']['future:data']={'opaque':[1,None]}
        self.d.good('load',{'action':'save','name':'unknown-test','document':doc})
        self.eq(self.d.good('load',{'action':'open','name':'unknown-test'}),doc,'unknown draft preserved')
        self.eq(self.d.call('load',{'action':'validate','workflow':doc['workflow']})['error']['code'],'NODE_UNRESOLVED','unknown cannot execute')
        self.eq(self.d.call('load',{'action':'open','name':'../outside'})['error']['code'],'DOCUMENT_NAME_DENIED','no arbitrary path IPC')
        self.eq(self.d.call('load',{'action':'validate','workflow':sample()['workflow'],'executable':'cmd.exe'})['error']['code'],'INVALID_BODY','no command extension')
    def test_T04_approval_enforced(self):
        self.start(sample(True)['workflow']);s=self.d.wait(lambda s:s['state']=='waiting-approval')
        key=read(self.d.dir/'latest.json')['key'];run=self.d.dir/'runs'/key
        self.eq(len(list(run.glob('mcp-*'))),0,'unapproved tool process absent')
        a=next(iter(s['approvals'].values()))
        self.eq(self.d.call('approve',{'approvalId':a['id'],'fingerprint':'stale','decision':True})['ok'],False,'stale grant denied')
        self.d.good('approve',{'approvalId':a['id'],'fingerprint':a['fingerprint'],'decision':True},id='approve-once')
        self.d.good('approve',{'approvalId':a['id'],'fingerprint':a['fingerprint'],'decision':True},id='approve-once')
        s=self.d.wait();self.eq(s['state'],'succeeded','approved real MCP completes')
        count=0
        for p in run.glob('mcp-*/server-ledger.sqlite'):
            db=sqlite3.connect(p);count+=db.execute("SELECT count(*) FROM records WHERE kind='effect-committed'").fetchone()[0];db.close()
        self.eq(count,1,'one effect despite repeated approval')
    def test_T05_new_runs_and_definition_pinning(self):
        w=sample()['workflow'];w['graph']['nodes'][2]['config']['delayMs']=900
        first=self.start(w);changed=deepcopy(w);changed['graph']['nodes'][0]['config']['value']='new draft';self.prepare(changed)
        s=self.d.wait();self.eq(s['identity']['workflow'],digest(w),'editing cannot mutate active definition')
        self.start(changed);second=self.d.wait();self.eq(second['runId']!=first['runId'],True,'multiple distinct runs, same executor')
        self.eq(second['identity']['workflow'],digest(changed),'second pinned definition')
    def test_T06_failure_cancel(self):
        w=sample()['workflow'];w['graph']['nodes'][2]['config']['fail']=True
        self.start(w);s=self.d.wait();self.eq(s['nodes']['main/model']['state'],'failed','actual failure')
        self.eq(s['nodes']['main/output']['state'],'skipped','failed output not executed')
        w=sample()['workflow'];w['graph']['nodes'][2]['config']['delayMs']=4000
        self.start(w);self.d.wait(lambda s:s['nodes']['main/model']['state']=='running');self.d.good('cancel');s=self.d.wait()
        self.eq(s['state'],'cancelled','cooperative cancel actual C1')
        self.eq(s['nodes']['main/output']['state'],'cancelled','downstream blocked')
    def test_T07_recovery_pending_approval(self):
        self.start(sample(True)['workflow']);first=self.d.wait(lambda s:s['state']=='waiting-approval');self.d.good('host.stop',{'mode':'suspend'});self.d.start()
        s=self.d.good('recover');self.eq(s['runId'],first['runId'],'same run recovery')
        self.eq(s['state'],'waiting-approval','never auto approved')
        self.eq(s['approvals'],first['approvals'],'same immutable action')
    def test_T08_duplicate_create_and_ownership(self):
        p=self.prepare(sample(True)['workflow']);a=self.d.good('create',{'token':p['token']},id='fixed-create')
        b=self.d.good('create',{'token':p['token']},id='fixed-create');self.eq(a['runId'],b['runId'],'create ACK idempotent')
        self.d.wait(lambda s:s['state']=='waiting-approval');other=old.Driver(self.d.dir)
        try:
            other.start();r=other.call('recover');self.eq(r['error']['code'],'CONTROLLER_ALREADY_OWNED','C1 single owner lock')
        finally:other.close()
    def test_T09_permissions_and_frame_limit(self):
        viewer=old.Driver(self.dir/'viewer',role='viewer')
        try:self.eq(viewer.call('host.start')['error']['code'],'PERMISSION_DENIED','backend role fixed')
        finally:viewer.close()
        # An unparseable oversized envelope has reserved empty correlation id.
        rid='oversize';self.d.p.stdin.write(json.dumps({'v':old.V,'kind':'request','id':rid,'op':'load','body':{'padding':'x'*263000}})+'\n');self.d.p.stdin.flush()
        self.eq(self.d.reply('')['error']['code'],'FRAME_SIZE','bounded request size')
    def test_T10_installed_profile_drift_recovery(self):
        self.start(sample(True)['workflow']);s=self.d.wait(lambda s:s['state']=='waiting-approval')
        key=read(self.d.dir/'latest.json')['key'];self.d.good('host.stop',{'mode':'suspend'})
        write(self.d.dir/'runs'/key/'profile.json',{'digest':'changed-installation'})
        self.d.start();r=self.d.call('recover')
        self.eq(r['error']['code'],'HOST_PROFILE_DRIFT','implementation drift fails closed')
        db=sqlite3.connect(self.d.dir/'runs'/key/'run.sqlite');state=json.loads(db.execute('SELECT state FROM snapshot WHERE id=1').fetchone()[0]);db.close()
        self.eq(state['runId'],s['runId'],'drift did not create a replacement run')
        self.eq(state['state'],'waiting-approval','drift did not auto approve')
    def test_T11_long_lived_read_identity_window(self):
        local_spec=importlib.util.spec_from_file_location('p007_endpoint_test',HERE/'executor.py')
        local=importlib.util.module_from_spec(local_spec);local_spec.loader.exec_module(local)
        Endpoint,Session=local.Endpoint,local.Session
        d=self.dir/'direct-endpoint';d.mkdir();ep=Endpoint(d,'normal');ep.s=Session(d/'run',sample(True)['workflow'])
        async def exercise():
            before=ep.s.runtime.snapshot
            for i in range(4105):
                r=await ep.request({'v':old.V,'kind':'request','id':'poll-'+str(i),'op':'status','body':{}})
                if not r['ok']:raise AssertionError(r)
            self.eq(ep.s.runtime.snapshot,before,'read polling never modifies C1')
            self.eq(len(ep.seen)<=4000,True,'bounded read replay window')
            r={'v':old.V,'kind':'request','id':'mutation-kept','op':'load','body':{'action':'validate','workflow':sample()['workflow']}}
            self.eq((await ep.request(r))['ok'],True,'validate accepted after 4105 polls')
            r['body']['workflow']['title']='different';self.eq((await ep.request(r))['error']['code'],'REQUEST_ID_CONFLICT','mutation id conflict still checked')
        try:asyncio.run(exercise())
        finally:ep.s.store.close();ep.s.system.close();ep.receipts.close()
    def test_T12_crash_unknown_not_blindly_rerun(self):
        w=sample()['workflow'];w['graph']['nodes'][2]['config']['delayMs']=6000
        before=self.start(w);self.d.wait(lambda s:s['nodes']['main/model']['state']=='running')
        self.d.good('host.crash-worker');self.d.start();self.d.good('recover');s=self.d.wait()
        self.eq(s['runId'],before['runId'],'crash retains original run identity')
        self.eq(s['state'],'unknown','in-flight result remains unknown')
        self.prepare(w);r=self.d.call('create',{'token':self.prepare(w)['token']})
        self.eq(r['error']['code'],'UNKNOWN_RUN_REQUIRES_RECONCILIATION','unknown run cannot be blindly replaced')

def main():
    global EVIDENCE
    EVIDENCE=HERE/'evidence'/('backend-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));EVIDENCE.mkdir()
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(BackendTests)
    with (EVIDENCE/'unittest.log').open('w',encoding='utf-8') as f:r=unittest.TextTestRunner(stream=f,verbosity=2).run(suite)
    summary={'tests':r.testsRun,'failures':len(r.failures),'errors':len(r.errors),'successful':r.wasSuccessful()}
    write(EVIDENCE/'summary.json',summary);write(HERE/'evidence/latest-backend.json',{'directory':str(EVIDENCE),'summary':summary});print(EVIDENCE,summary)
    if not r.wasSuccessful():print((EVIDENCE/'unittest.log').read_text(encoding='utf-8'))
    return 0 if r.wasSuccessful() else 1
if __name__=='__main__':raise SystemExit(main())
