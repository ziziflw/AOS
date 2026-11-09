"""Deterministic assertions on actual SDK HTTP, original C1 state and persisted snapshots."""
import asyncio,importlib.util,json,sqlite3,unittest,traceback
from copy import deepcopy
from datetime import datetime,timezone
from boot import HERE,read,write,ContractError
s=importlib.util.spec_from_file_location('p008_endpoint_test',HERE/'executor.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
from model_profile import sample,make_node,requirements,edge
EVIDENCE=HERE/'evidence'/('models-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
EVIDENCE.mkdir();SESSIONS=[]
class Tests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):self.sessions=[];self.dir=EVIDENCE/self._testMethodName;self.dir.mkdir()
    def session(self,w=None):
        d=self.dir/str(len(self.sessions));w=w or sample()['workflow'];write(self.dir/('input-'+str(len(self.sessions))+'.json'),w)
        x=m.Session(d,w);self.sessions.append(x);return x
    async def asyncTearDown(self):
        for x in self.sessions:
            try:
                await x.runtime.close();await x.registry.close();x.export();x.release_resources();x.store.close();x.system.close()
            except Exception:write(self.dir/'cleanup-failure.json',{'traceback':traceback.format_exc()});raise
    async def drive(self,tid='p08.openai.text',mode=None):
        x=self.session(sample(tid,mode)['workflow']);state=await x.runtime.drive();return x,state
    async def test_T01_two_official_sdks_real_http(self):
        for tid,path in [('p08.openai.text','/v1/chat/completions'),('p08.anthropic.text','/v1/messages')]:
            x,s=await self.drive(tid);self.assertEqual(s['state'],'succeeded');self.assertEqual(s['scopes']['main']['result'],'离线 HTTP 合成响应')
            self.assertEqual(x.fixture.rows[0]['path'],path);self.assertTrue(x.fixture.rows[0]['authorizationPresent']);self.assertEqual(len(x.fixture.rows),1)
            self.assertEqual(s['usage'],{'spentTokens':19,'reservedTokens':0,'costMinor':0});self.assertEqual(s['nodes']['main/model']['modelUsage'],{'inputTokens':12,'outputTokens':7})
            self.assertEqual(s['modelCosts']['estimatedMinor'],1);self.assertFalse(s['modelCosts']['invoiceVerified'])
    async def test_T02_unsupported_params_alias_versions_and_types(self):
        for change in ('temperature','alias','version','type'):
            w=sample('p08.anthropic.text')['workflow'];n=w['graph']['nodes'][1]
            if change=='temperature':n['config']['temperature']=.4
            if change=='alias':n['config']['credentialAlias']='credential:real-user'
            if change=='version':n['typeVersion']='99.0.0'
            if change=='type':n['config']['maxOutputTokens']='64'
            with self.assertRaises(ContractError):m.validate(w)
    async def test_T03_structured_json_both_protocols(self):
        for tid in ('p08.openai.json','p08.anthropic.json'):
            x,s=await self.drive(tid);self.assertEqual(s['state'],'succeeded');self.assertEqual(s['nodes']['main/model']['outputs']['out']['payload'],{'answer':'离线结构化响应'})
            self.assertTrue('response_format' in x.fixture.rows[0]['body'] or 'output_config' in x.fixture.rows[0]['body'])
    async def test_T04_wrong_output_schema_fails_no_downstream(self):
        x,s=await self.drive('p08.openai.json','badjson');self.assertEqual(s['state'],'failed');self.assertEqual(s['nodes']['main/model']['error']['code'],'PORT_VALUE_INVALID')
        self.assertEqual(s['nodes']['main/output']['state'],'skipped');self.assertEqual(s['usage']['spentTokens'],19)
    async def test_T05_rate_and_error_no_sdk_retries(self):
        for tid in ('p08.openai.text','p08.anthropic.text'):
            for mode,code in [('rate','MODEL_RATE_LIMIT'),('error','MODEL_HTTP_400')]:
                x,s=await self.drive(tid,mode);self.assertEqual(s['state'],'failed');self.assertEqual(s['nodes']['main/model']['error']['code'],code);self.assertEqual(len(x.fixture.rows),1)
    async def test_T06_timeouts_and_lost_response_unknown(self):
        for mode in ('delay','lost'):
            x,s=await self.drive(mode=mode);self.assertEqual(s['state'],'unknown');self.assertEqual(len(x.fixture.rows),1);self.assertEqual(s['usage']['reservedTokens'],576);self.assertEqual(s['modelCosts']['reservedMinor'],10)
    async def test_T07_cancel_keeps_unknown_consumption(self):
        x=self.session(sample(mode='delay')['workflow']);task=asyncio.create_task(x.runtime.drive())
        for _ in range(300):
            if x.fixture.rows:break
            await asyncio.sleep(.005)
        self.assertEqual(len(x.fixture.rows),1);x.runtime.cancel();s=await task;self.assertEqual(s['state'],'unknown');self.assertTrue(s['cancelRequested']);self.assertEqual(s['nodes']['main/output']['state'],'cancelled');self.assertEqual(s['usage']['reservedTokens'],576)
        await asyncio.sleep(.1);self.assertEqual(x.runtime.snapshot['nodes']['main/output']['state'],'cancelled')
    async def test_T08_missing_usage_retains_reservation(self):
        for tid in ('p08.openai.text','p08.anthropic.text'):
            x,s=await self.drive(tid,'missing');self.assertEqual(s['state'],'succeeded');self.assertIsNone(s['nodes']['main/model']['modelUsage']);self.assertEqual(s['usage']['reservedTokens'],576);self.assertEqual(s['modelCosts']['reservedMinor'],10)
    def parallel(self,*,limit=4096,money=100,concurrency=2):
        w=sample(mode='slow')['workflow'];nodes=w['graph']['nodes'];second=deepcopy(nodes[1]);second['id']='model2';nodes.insert(2,second);nodes.insert(3,make_node('p08.join','join'))
        w['graph']['edges']=[edge('text','model',index=0),edge('text','model2',index=1),edge('model','join',inp='items',index=2),edge('model2','join',inp='items',order=1,index=3),edge('join','output',index=4)]
        w['executionPolicy']['budget'].update(maxTokens=limit,maxCostMinor=money);w['executionPolicy']['concurrencyLimit']=concurrency
        return w
    async def test_T09_parallel_atomic_budget_competition(self):
        x=self.session(self.parallel(limit=600));s=await x.runtime.drive();self.assertEqual(s['state'],'failed');self.assertEqual(len(x.fixture.rows),1);self.assertEqual(s['nodes']['main/model2']['error']['code'],'TOKEN_BUDGET_EXCEEDED')
        events=x.store.events();self.assertEqual(len([e for e in events if e['kind']=='node-dispatched' and e['key'] in ('main/model','main/model2')]),1)
    async def test_T10_concurrency_limit_and_independent_reservations(self):
        for concurrency in (1,2):
            x=self.session(self.parallel(concurrency=concurrency));s=await x.runtime.drive();self.assertEqual(s['state'],'succeeded');self.assertEqual(len(x.fixture.rows),2);self.assertEqual(x.fixture.peak,concurrency);self.assertEqual(s['usage']['spentTokens'],38);self.assertEqual(s['usage']['reservedTokens'],0)
    async def test_T11_money_and_input_gate_before_request(self):
        x=self.session(self.parallel(money=10));s=await x.runtime.drive();self.assertEqual(len(x.fixture.rows),1);self.assertEqual(s['nodes']['main/model2']['error']['code'],'COST_BUDGET_EXCEEDED')
        w=sample()['workflow'];w['graph']['nodes'][0]['config']['value']='x'*600;x=self.session(w);s=await x.runtime.drive();self.assertEqual(x.fixture.rows,[]);self.assertEqual(s['nodes']['main/model']['error']['code'],'MODEL_INPUT_ADMISSION_LIMIT')
    async def test_T12_backend_approval_blocks_wire(self):
        w=sample()['workflow'];w['graph']['nodes'][1]['policy']['approval']='always';x=self.session(w);s=await x.runtime.drive();self.assertEqual(s['state'],'waiting-approval');self.assertEqual(x.fixture.rows,[])
        a=next(iter(s['approvals'].values()));self.assertEqual(s['nodes']['main/model']['attempts'],[])
        with self.assertRaises(ContractError):x.runtime.approve(a['id'],'stale')
        x.runtime.approve(a['id'],a['fingerprint']);x.runtime.approve(a['id'],a['fingerprint']);s=await x.runtime.drive();self.assertEqual(s['state'],'succeeded');self.assertEqual(len(x.fixture.rows),1)
    async def test_T13_redaction_from_error_and_model_output(self):
        for mode in ('secret','leak'):
            x,s=await self.drive(mode=mode);self.assertEqual(s['state'],'failed');self.assertNotIn('fixture-secret-',json.dumps(s));self.assertNotIn('fixture-secret-',json.dumps(x.store.events()));self.assertNotIn('fixture-secret-',json.dumps(x.fixture.rows))
    async def test_T14_windows_vault_owned_alias(self):
        from credentials import Vault
        v=Vault();alias=v.create_fixture()
        try:
            secret=v.resolve(alias);self.assertTrue(secret.startswith('fixture-secret-'))
            with self.assertRaises(ContractError):v.resolve('arbitrary-user-alias')
        finally:v.close()
        with self.assertRaises(ContractError):v.resolve(alias)
    async def test_T15_recovery_no_replay_unknown_holds(self):
        x=self.session();rt=x.runtime
        # Durable dispatch then abrupt controller loss. No result can be inferred from intent.
        rt._begin('main/text',{});rt._terminal('main/text','succeeded',outputs=rt._envelopes('main/text',{'out':'restart'},rt.snapshot['nodes']['main/text']['attempts'][-1]['id']))
        _,inputs=rt._dependencies('main/model');rt._begin('main/model',inputs);before=rt.snapshot
        x.export('interrupted');x.store.close();x.system.close();x.release_resources();self.sessions.remove(x)
        y=m.Session(x.dir,rt.c.w,recover=True);self.sessions.append(y);s=await y.runtime.drive();self.assertEqual(s['runId'],before['runId']);self.assertEqual(s['state'],'unknown');self.assertEqual(y.fixture.rows,[]);self.assertEqual(s['usage']['reservedTokens'],576)
    async def test_T16_sqlite_authority_and_fixed_revision(self):
        x,s=await self.drive();db=sqlite3.connect(x.dir/'run.sqlite');stored=json.loads(db.execute('SELECT state FROM snapshot WHERE id=1').fetchone()[0]);self.assertEqual(stored,s);self.assertEqual(db.execute('pragma integrity_check').fetchone()[0],'ok');db.close()
        self.assertEqual(s['workflowRevision'],x.runtime.c.w['version']['revision']);self.assertEqual(x.store.events()[-1]['seq'],s['seq'])
    async def test_T17_environment_binding_cannot_redirect_provider(self):
        x=self.session();original=deepcopy(x.runtime.environment)
        for change,code in [('connection','MODEL_CONNECTION_DENIED'),('credential','MODEL_CREDENTIAL_BINDING_DENIED'),('target','MODEL_BINDING_MISMATCH')]:
            x.runtime.environment=deepcopy(original)
            if change=='connection':x.runtime.environment['connections']['connection:p08-model']['programRef']='program:arbitrary'
            if change=='credential':x.runtime.environment['credentials']['secret:p08-model']['status']='unbound'
            if change=='target':x.runtime.environment['services']['p08.openai.text']['target']['model']='real-billable-model'
            with self.assertRaises(ContractError) as caught:x.runtime._validate_environment()
            self.assertEqual(caught.exception.code,code);self.assertEqual(x.fixture.rows,[])
        x.runtime.environment=original
    async def test_T18_original_accounting_counterexample_actual_sdk(self):
        w=sample(mode='large')['workflow'];w['graph']['nodes'][1]['config'].update(maxInputTokens=1024,maxOutputTokens=128,maxCallCostMinor=12)
        x=self.session(w);s=await x.runtime.drive();self.assertEqual(s['state'],'succeeded');self.assertEqual(s['usage']['spentTokens'],1000);self.assertEqual(s['nodes']['main/model']['modelUsage'],{'inputTokens':900,'outputTokens':100});self.assertEqual(s['usage']['reservedTokens'],0)
    async def test_T19_missing_usage_blocks_next_sequential_request(self):
        w=sample(mode='missing')['workflow'];nodes=w['graph']['nodes'];second=make_node('p08.openai.text','model2');nodes.insert(2,second)
        w['graph']['edges']=[edge('text','model',index=0),edge('model','model2',index=1),edge('model2','output',index=2)];w['executionPolicy']['budget']['maxTokens']=600
        x=self.session(w);s=await x.runtime.drive();self.assertEqual(s['state'],'failed');self.assertEqual(s['nodes']['main/model']['state'],'succeeded');self.assertEqual(s['nodes']['main/model2']['error']['code'],'TOKEN_BUDGET_EXCEEDED');self.assertEqual(len(x.fixture.rows),1);self.assertEqual(s['usage']['reservedTokens'],576)
    async def test_T20_second_claim_cannot_mutate_manifest_or_credential(self):
        x=self.session();before=read(x.dir/'workflow.json');secret=x.vault.resolve(x.alias);seq=x.runtime.snapshot['seq']
        with self.assertRaises(ContractError) as caught:m.Session(x.dir,sample('p08.anthropic.text')['workflow'])
        self.assertEqual(caught.exception.code,'CONTROLLER_ALREADY_OWNED');self.assertEqual(read(x.dir/'workflow.json'),before);self.assertEqual(x.vault.resolve(x.alias),secret);self.assertEqual(x.runtime.snapshot['seq'],seq)

if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
    summary={'methods':result.testsRun,'failures':[(str(t),e) for t,e in result.failures],'errors':[(str(t),e) for t,e in result.errors],'passed':result.wasSuccessful(),'scope':'real SDK / local synthetic HTTP, not real inference'}
    write(EVIDENCE/'summary.json',summary);write(HERE/'evidence/latest-models.json',{'directory':str(EVIDENCE),**summary});print(EVIDENCE);raise SystemExit(not result.wasSuccessful())
