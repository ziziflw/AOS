import importlib.util,unittest,sqlite3,json,time
from datetime import datetime,timezone
from boot import HERE,read,write
s=importlib.util.spec_from_file_location('p008_host_endpoint',HERE/'executor.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
s=importlib.util.spec_from_file_location('p006_host_driver',HERE.parent/'p0-06/test_host.py');old=importlib.util.module_from_spec(s);s.loader.exec_module(old)
old.HERE=HERE;old.HOST=HERE/'host/target/debug/host-probe.exe'
OUT=HERE/'evidence'/('host-models-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));OUT.mkdir()
class Tests(unittest.TestCase):
    def setUp(self):self.dir=OUT/self._testMethodName;self.dir.mkdir();self.d=old.Driver(self.dir/'session');self.d.start()
    def tearDown(self):self.d.close()
    def start(self,w):p=self.d.good('load',{'action':'validate','workflow':w});return self.d.good('create',{'token':p['token']})
    def test_H01_real_rust_ipc_sdk_sqlite(self):
        h=self.d.good('health');self.assertEqual(h['authority'],'C1/SQLite');self.assertEqual(h['providers'][1]['status'],'unconfigured-authorization-required')
        self.start(m.profile.sample()['workflow']);state=self.d.wait();self.assertEqual(state['state'],'succeeded')
        p=self.d.dir/'runs'/read(self.d.dir/'latest.json')['key'];db=sqlite3.connect(p/'run.sqlite');self.assertEqual(state,json.loads(db.execute('select state from snapshot where id=1').fetchone()[0]));db.close();self.assertEqual(len(read(p/'http/http-ledger.json')['requests']),1)
        write(self.dir/'observed.json',state)
    def test_H02_real_mcp_regression_in_extended_host(self):
        self.start(m.profile.sample(True)['workflow']);s=self.d.wait(lambda s:s['state']=='waiting-approval');a=next(iter(s['approvals'].values()))
        self.d.good('approve',{'approvalId':a['id'],'fingerprint':a['fingerprint'],'decision':True});self.assertEqual(self.d.wait()['state'],'succeeded')
    def test_H03_sdk_cancel_unknown_host_restart_no_resubmit(self):
        self.start(m.profile.sample(mode='delay')['workflow']);self.d.wait(lambda s:s['nodes']['main/model']['state']=='running');self.d.good('cancel');s=self.d.wait();self.assertEqual(s['state'],'unknown');run=s['runId'];self.d.good('host.stop',{'mode':'suspend'});self.d.start();r=self.d.good('recover');self.assertEqual(r['runId'],run);self.assertEqual(self.d.wait()['state'],'unknown');self.assertEqual(self.d.call('create',{'token':'arbitrary'})['ok'],False)
    def test_H04_model_approval_survives_worker_crash(self):
        w=m.profile.sample()['workflow'];w['graph']['nodes'][1]['policy']['approval']='always';self.start(w);s=self.d.wait(lambda s:s['state']=='waiting-approval');run=s['runId'];self.d.good('host.crash-worker');self.d.start();self.d.good('recover');s=self.d.wait(lambda s:s['state']=='waiting-approval');self.assertEqual(s['runId'],run);self.assertEqual(s['nodes']['main/model']['attempts'],[])
        self.d.good('cancel');self.assertEqual(self.d.wait()['state'],'cancelled')
if __name__=='__main__':
    r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests));write(OUT/'summary.json',{'methods':r.testsRun,'passed':r.wasSuccessful(),'failures':[(str(t),e) for t,e in r.failures],'errors':[(str(t),e) for t,e in r.errors]});write(HERE/'evidence/latest-host.json',{'directory':str(OUT),'passed':r.wasSuccessful()});print(OUT);raise SystemExit(not r.wasSuccessful())
