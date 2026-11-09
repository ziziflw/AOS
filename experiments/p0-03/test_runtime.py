"""Deterministic semantic assertions; each run saves input, DB, events and outputs."""
import asyncio, hashlib, json, os, sqlite3, subprocess, sys, time, traceback, unittest
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from common import ContractError, read, write
from contracts import SchemaClient, Contracts
from fixtures import generate, FIX, BASE, ROOT, HERE
from harness import Session, inputs, approve_all
from mocks import MockRegistry, SyntheticSystem
from store import StateStore

EVIDENCE=None
VALIDATOR=None

class RuntimeTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.dir=EVIDENCE/self._testMethodName; self.dir.mkdir()
        self.sessions=[]; self.comparisons=[]
    async def asyncTearDown(self):
        for s in reversed(self.sessions):
            s.export("assertion-point")
            await s.close()
        write(self.dir/"assertions.json",self.comparisons)
    def eq(self,actual,expected,label):
        self.comparisons.append({"label":label,"expected":deepcopy(expected),"actual":deepcopy(actual),"passed":actual==expected})
        write(self.dir/"assertions.json",self.comparisons)
        self.assertEqual(actual,expected,label)
    def session(self,name,*,label=None,plan=None,change=None,environment=None,**kwargs):
        w,r,c=inputs(name)
        if change: change(w,r)
        s=Session(self.dir/(label or name),VALIDATOR,workflow=w,request=r,catalog_path=c,plan=plan,environment=environment,**kwargs)
        self.sessions.append(s); return s
    async def run_to(self,s):
        return await asyncio.wait_for(s.runtime.drive(),5)
    async def wait_state(self,runtime,key,state):
        for _ in range(500):
            if runtime.snapshot["nodes"][key]["state"]==state: return
            await asyncio.sleep(.002)
        self.fail("Node did not reach "+state)
    def calls(self,s,key):
        return [r for r in s.system.dump()["calls"] if r["node"]==key]
    def pending(self,s):
        return [a for a in s.runtime.snapshot["approvals"].values() if a["status"]=="pending"]
    def grant(self,s):
        a=self.pending(s)[0]; s.runtime.approve(a["id"],a["fingerprint"]); return a
    def raw_state(self,path):
        con=sqlite3.connect(path)
        try: return json.loads(con.execute("SELECT state FROM snapshot WHERE id=1").fetchone()[0])
        finally: con.close()

    async def test_T01_serial(self):
        s=self.session("serial")
        st=await self.run_to(s)
        self.eq(st["state"],"succeeded","run terminal")
        self.eq(st["scopes"]["main"]["result"],"seedB","typed final output")
        events=s.store.events()
        committed=next(e["seq"] for e in events if e["kind"]=="node-terminal" and e.get("key")=="main/A")
        begun=next(e["seq"] for e in events if e["kind"]=="node-dispatched" and e.get("key")=="main/B")
        self.eq(committed<begun,True,"B dispatch follows durable A success")
        self.eq(st["nodes"]["main/B"]["attempts"][0]["inputs"]["in"],"seed","B used A valid payload")
        self.eq(any(e["kind"]=="node-ready" for e in events),True,"ready distinguished from dependency wait")

    async def test_T02_parallel_and_limit(self):
        s=self.session("parallel",plan={"B":{"barrier":"pair","delay":.015},"C":{"barrier":"pair"}})
        st=await self.run_to(s)
        self.eq(st["state"],"succeeded","parallel success")
        b,c=self.calls(s,"main/B")[0],self.calls(s,"main/C")[0]
        self.eq(max(b["started"],c["started"])<min(b["finished"],c["finished"]),True,"actual adapter intervals overlap")
        self.eq(st["scopes"]["main"]["result"],["seedB","seedC"],"order is edge order despite reverse completion")
        d=self.calls(s,"main/D")[0]
        self.eq(d["started"]>=max(b["finished"],c["finished"]),True,"D waits for both")
        one=self.session("parallel",label="limit-one",plan={"B":{"delay":.005},"C":{"delay":.005}},
                         change=lambda w,r:w["executionPolicy"].update(concurrencyLimit=1))
        await self.run_to(one)
        b,c=self.calls(one,"main/B")[0],self.calls(one,"main/C")[0]
        self.eq(b["finished"]<=c["started"] or c["finished"]<=b["started"],True,"global limit one serializes workers")
        mixed=self.session("parallel",label="mixed-group-limits",plan={"B":{"delay":.005},"C":{"delay":.005}},
                           change=lambda w,r:w["graph"]["nodes"][1]["policy"].update(concurrencyLimit=1))
        await self.run_to(mixed)
        b,c=self.calls(mixed,"main/B")[0],self.calls(mixed,"main/C")[0]
        self.eq(b["finished"]<=c["started"],True,"new peer cannot exceed running peer's stricter group limit")

    async def test_T03_condition_and_exclusive_join(self):
        s=self.session("conditional")
        st=await self.run_to(s)
        self.eq(st["state"],"succeeded","exclusive conditional merge completes")
        self.eq(st["nodes"]["main/C"]["state"],"skipped","unselected C is skipped")
        self.eq(len(self.calls(s,"main/C")),0,"unselected adapter never called")
        self.eq(st["scopes"]["main"]["result"],"seedB","only selected branch forwarded")

    async def test_T04_join_skipped_failed_cancelled(self):
        skip=self.session("conditional-all")
        st=await self.run_to(skip)
        self.eq(st["state"],"skipped","strict all join does not silently drop skipped required branch")
        self.eq(st["nodes"]["main/M"]["state"],"skipped","join settles without waiting forever")
        failed=self.session("parallel",label="failed",plan={"B":{"fail":True}})
        st=await self.run_to(failed)
        self.eq(st["state"],"failed","one failed branch fails workflow")
        self.eq(len(self.calls(failed,"main/D")),0,"D never executes with missing failure output")
        cancelled=self.session("parallel",label="branch-cancel",plan={"B":{"wait":True}})
        driver=asyncio.create_task(cancelled.runtime.drive())
        await self.wait_state(cancelled.runtime,"main/B","running")
        cancelled.runtime.cancel_node("main/B")
        st=await asyncio.wait_for(driver,3)
        self.eq(st["nodes"]["main/B"]["state"],"cancelled","cooperative branch cancellation acknowledged")
        self.eq(st["nodes"]["main/D"]["state"],"skipped","join handles cancelled dependency")
        self.eq(st["state"],"cancelled","run cancellation remains distinct from failure")

    async def test_T05_bounded_loop_and_iterations(self):
        s=self.session("c",plan={"repairAgent":{"successAt":1}})
        st=await asyncio.wait_for(approve_all(s.runtime),8)
        self.eq(st["state"],"succeeded","original P0-02 C graph executes with explicit test approvals")
        repairs=[(k,v) for k,v in st["nodes"].items() if v["nodeId"]=="repairAgent"]
        self.eq(len(repairs),2,"two repair iterations")
        self.eq([st["scopes"][v["scope"]]["iteration"] for k,v in repairs],[[0],[1]],"iteration identities")
        self.eq(len({v["attempts"][0]["id"] for k,v in repairs}),2,"iteration attempt IDs distinct")
        self.eq(len({v["operationId"] for k,v in repairs}),2,"new iteration has new logical operation")
        self.eq([v["attempts"][0]["number"] for k,v in repairs],[1,1],"iteration is not retry")
        bad=self.session("c",label="limit-exhausted",plan={"repairAgent":{"successAt":99}})
        st=await asyncio.wait_for(approve_all(bad.runtime),8)
        self.eq(st["state"],"failed","loop exhaustion fails rather than publish invalid result")
        self.eq(st["nodes"]["main/repair"]["error"]["code"],"LOOP_LIMIT_EXCEEDED","bounded failure reason")
        self.eq(len([v for v in st["nodes"].values() if v["nodeId"]=="repairAgent"]),2,"no third iteration")
        self.eq(len(self.calls(bad,"main/output")),0,"invalid output not released")

    async def test_T06_safe_retry_attempt_history(self):
        def retry(w,r): w["graph"]["nodes"][1]["policy"].update(maxAttempts=2,retryMode="safe")
        s=self.session("serial",change=retry,plan={"B":{"failFirst":True}})
        st=await self.run_to(s); attempts=st["nodes"]["main/B"]["attempts"]
        self.eq(st["state"],"succeeded","safe retry recovers")
        self.eq([a["state"] for a in attempts],["failed","succeeded"],"both attempt outcomes retained")
        self.eq(len({a["id"] for a in attempts}),2,"different attempt IDs")
        self.eq(len({c["operation"] for c in self.calls(s,"main/B")}),1,"logical operation identity stable across attempts")

    async def test_T07_response_lost_unknown_no_retry(self):
        s=self.session("effect",plan={"B":{"lostResponse":True}})
        await self.run_to(s)
        self.eq(len(s.system.dump()["effects"]),0,"unapproved operation not executed")
        self.grant(s)
        st=await self.run_to(s)
        self.eq(st["state"],"unknown","response loss is unknown, not ordinary failure")
        self.eq(st["nodes"]["main/B"]["state"],"unknown","node unknown")
        self.eq([e["count"] for e in s.system.dump()["effects"]],[1],"synthetic external operation happened exactly once in this run")
        self.eq(len(st["nodes"]["main/B"]["attempts"]),1,"no blind retry")
        self.eq(len(self.calls(s,"main/C")),0,"unknown output never advances descendants")
        directory=s.directory
        s.export("before-restart"); await s.close(); self.sessions.remove(s)
        recovered=Session(directory,VALIDATOR,recover=True); self.sessions.append(recovered)
        await self.run_to(recovered)
        self.eq([e["count"] for e in recovered.system.dump()["effects"]],[1],"recovery does not replay unknown effect")

    async def test_T08_process_crashes_and_recovery(self):
        for mode,name in (("after-success","serial"),("during-success","serial"),("waiting-approval","effect")):
            s=self.session(name,label=mode)
            directory=s.directory
            run_id=s.runtime.snapshot["runId"]
            await s.close(); self.sessions.remove(s)
            proc=await asyncio.to_thread(subprocess.run,[sys.executable,"-B","-X","utf8",str(HERE/"crash_worker.py"),str(directory),mode],
                                         capture_output=True,text=True,encoding="utf-8",timeout=20,
                                         creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
            write(directory/"worker-result.json",{"returnCode":proc.returncode,"stdout":proc.stdout,"stderr":proc.stderr})
            self.eq(proc.returncode,73,"child process terminated at "+mode)
            before=self.raw_state(directory/"run.sqlite")
            write(directory/"persisted-before-recovery.json",before)
            q=Session(directory,VALIDATOR,recover=True); self.sessions.append(q)
            self.eq(q.runtime.snapshot["runId"],run_id,"same run instance after "+mode)
            if mode=="after-success":
                st=await self.run_to(q)
                self.eq(st["state"],"succeeded","continue from committed node")
                self.eq(len(self.calls(q,"main/A")),1,"committed A not re-executed")
            elif mode=="during-success":
                self.eq(before["nodes"]["main/A"]["state"],"running","uncommitted completion rolled back")
                st=await self.run_to(q)
                self.eq(st["state"],"unknown","unconfirmed in-flight operation not guessed safe")
                self.eq(len(self.calls(q,"main/A")),1,"no repeat after commit uncertainty")
                self.eq(len(self.calls(q,"main/B")),0,"B not dispatched from uncommitted value")
            else:
                st=await self.run_to(q)
                self.eq(st["state"],"waiting-approval","pending approval survives restart")
                self.eq(len(q.system.dump()["effects"]),0,"restart never automatically approves")
                self.grant(q); st=await self.run_to(q)
                self.eq(st["state"],"succeeded","resume after explicit valid approval")
                self.eq([e["count"] for e in q.system.dump()["effects"]],[1],"one approved synthetic effect")

    async def test_T09_cancel_queued_running_and_approval(self):
        queued=self.session("serial",label="queued")
        queued.runtime.cancel(); st=await self.run_to(queued)
        self.eq(st["state"],"cancelled","cancel before dispatch")
        self.eq(queued.system.dump()["calls"],[],"no queued handler executed")
        running=self.session("serial",label="running",plan={"B":{"wait":True}})
        driver=asyncio.create_task(running.runtime.drive()); await self.wait_state(running.runtime,"main/B","running")
        running.runtime.cancel(); st=await asyncio.wait_for(driver,3)
        self.eq(st["state"],"cancelled","cooperative running cancellation")
        self.eq(len(self.calls(running,"main/C")),0,"cancelled B cannot dispatch C")
        waiting=self.session("effect",label="waiting")
        await self.run_to(waiting); token=self.pending(waiting)[0]
        waiting.runtime.cancel()
        with self.assertRaises(ContractError): waiting.runtime.approve(token["id"],token["fingerprint"])
        st=await self.run_to(waiting)
        self.eq(st["state"],"cancelled","approval-wait cancellation")
        self.eq(waiting.system.dump()["effects"],[],"cancelled token cannot cause effect")

    async def test_T09_uncooperative_cancel_is_unknown(self):
        s=self.session("serial",plan={"B":{"wait":True,"cooperative":False}})
        driver=asyncio.create_task(s.runtime.drive()); await self.wait_state(s.runtime,"main/B","running")
        s.runtime.cancel(); st=await asyncio.wait_for(driver,3)
        self.eq(st["state"],"unknown","unconfirmed cancellation is not falsely confirmed")
        self.eq(len(self.calls(s,"main/C")),0,"no stale continuation")
        s.registry.release.set(); await asyncio.sleep(.01)
        self.eq(s.runtime.snapshot["nodes"]["main/B"]["outputs"],{},"late result never published")
        self.eq(any(e["kind"]=="late-result-discarded" for e in s.store.events()),True,"late result audited")

    async def test_T10_single_authority_and_transaction_view(self):
        s=self.session("serial")
        with self.assertRaises(ContractError) as error: StateStore(s.directory/"run.sqlite")
        self.eq(error.exception.code,"CONTROLLER_ALREADY_OWNED","second controller refused before dispatch")
        fake=s.runtime.snapshot; fake["nodes"]["main/A"]["state"]="succeeded"
        write(s.directory/"fake-ui-log.json",fake)
        self.eq(s.store.load()["nodes"]["main/A"]["state"],"queued","caller snapshot and fake log cannot mutate authority")
        st=await self.run_to(s)
        self.eq(self.raw_state(s.directory/"run.sqlite"),st,"memory return equals committed SQLite snapshot")
        events=s.store.events()
        self.eq([e["seq"] for e in events],list(range(1,st["seq"]+1)),"events and snapshot one sequence")
        self.eq(s.store.db.execute("PRAGMA integrity_check").fetchone()[0],"ok","SQLite integrity")
        q=self.session("serial",label="corrupt")
        q.store.db.execute("UPDATE snapshot SET checksum='not-valid' WHERE id=1")
        with self.assertRaises(ContractError) as error: q.store.load()
        self.eq(error.exception.code,"SNAPSHOT_CORRUPT","corruption is rejected, not independently interpreted")
        # Restore only the synthetic corruption, using the original controller's actual value.
        from common import digest
        q.store.db.execute("UPDATE snapshot SET checksum=? WHERE id=1",(digest(q.runtime.snapshot),))

    async def test_approval_pending_denied_and_duplicate(self):
        s=self.session("effect",label="approved")
        st=await self.run_to(s)
        self.eq(st["state"],"waiting-approval","policy=policy still gates trusted write metadata")
        self.eq(s.system.dump()["effects"],[],"no preapproval side effect")
        a=self.grant(s)
        self.eq(s.runtime.approve(a["id"],a["fingerprint"]),"granted","duplicate approval is idempotent")
        st=await self.run_to(s)
        self.eq(st["state"],"succeeded","valid approved execution")
        self.eq([e["count"] for e in s.system.dump()["effects"]],[1],"duplicate approval never duplicates effect")
        denied=self.session("effect",label="denied")
        await self.run_to(denied); a=self.pending(denied)[0]
        denied.runtime.approve(a["id"],a["fingerprint"],False)
        st=await self.run_to(denied)
        self.eq(st["state"],"failed","denial is explicit failure")
        self.eq(denied.system.dump()["effects"],[],"denied operation never invoked")

    async def test_approval_content_binding_and_expiry(self):
        s=self.session("effect",label="old")
        await self.run_to(s); a=self.pending(s)[0]
        with self.assertRaises(ContractError) as error: s.runtime.approve(a["id"],"0"*64)
        self.eq(error.exception.code,"APPROVAL_CONTENT_MISMATCH","changed fingerprint cannot approve")
        changed=self.session("effect",label="changed",change=lambda w,r:w["graph"]["nodes"][1]["config"].update(suffix="different-operation"))
        await self.run_to(changed)
        with self.assertRaises(ContractError): changed.runtime.approve(a["id"],a["fingerprint"])
        self.eq(changed.system.dump()["effects"],[],"old run approval cannot authorize changed content")
        self.eq(changed.runtime.snapshot["runId"]!=s.runtime.snapshot["runId"],True,"new run has independent identity")
        exp=self.session("effect",label="expired",approval_ttl=.001)
        await self.run_to(exp); expired=self.pending(exp)[0]
        await asyncio.sleep(.01)
        with self.assertRaises(ContractError) as error: exp.runtime.approve(expired["id"],expired["fingerprint"])
        self.eq(error.exception.code,"APPROVAL_EXPIRED","expired approval rejected")
        self.eq(exp.system.dump()["effects"],[],"expiry causes zero execution")

    async def test_approval_changed_definition_recovery_rejected(self):
        s=self.session("effect")
        await self.run_to(s); directory=s.directory; original=read(directory/"workflow.json")
        write(directory/"workflow.original.json",original)
        await s.close(); self.sessions.remove(s)
        changed=deepcopy(original); changed["graph"]["nodes"][1]["config"]["suffix"]="changed-after-approval-request"
        write(directory/"workflow.json",changed)
        with self.assertRaises(ContractError) as error: Session(directory,VALIDATOR,recover=True)
        self.eq(error.exception.code,"RECOVERY_DEFINITION_MISMATCH","cannot reuse old pending approval under changed workflow")

    async def test_P02_original_a_b_and_output_types(self):
        for name in ("a","b"):
            s=self.session(name)
            st=await self.run_to(s)
            self.eq(st["state"],"succeeded","unmodified P0-02 scenario "+name)
            self.eq(st["workflowRevision"],"scenario-"+name+"-r1","original revision retained")
            self.eq(isinstance(st["scopes"]["main"]["result"],dict),True,"structured output remains object")

    async def test_data_null_error_and_resource_validation(self):
        null=self.session("nullable")
        st=await self.run_to(null)
        self.eq(st["state"],"succeeded","explicit nullable passes")
        self.eq(st["nodes"]["main/B"]["outputs"]["out"]["payload"],None,"null preserved")
        bad=self.session("bad-output")
        st=await self.run_to(bad)
        self.eq(st["state"],"failed","Error object cannot masquerade as Text")
        self.eq(st["nodes"]["main/B"]["error"]["code"],"PORT_VALUE_INVALID","backend output type rejection")
        self.eq(len(self.calls(bad,"main/C")),0,"invalid output not forwarded")
        structured=self.session("a",label="invalid-model-output",plan={"modelA":{"outputOverride":{"out":{"answer":123}}}})
        st=await self.run_to(structured)
        self.eq(st["state"],"failed","missing/invalid structured fields rejected at runtime")
        self.eq(len(self.calls(structured,"main/review")),0,"review not called on invalid candidate")
        resource=self.session("b",label="missing-resource",change=lambda w,r:r["inputs"]["request"]["source"].update(resourceUri="workspace:source/missing.txt"))
        st=await self.run_to(resource)
        self.eq(st["state"],"failed","logical URI existence checked at use")
        self.eq(st["nodes"]["main/tool"]["error"]["code"],"RESOURCE_NOT_BOUND","logical resource failure not file path fallback")

    async def test_preflight_rejects_unknown_versions_fields_and_parameters(self):
        base_w,base_r,cat=inputs("a")
        def clone(): return deepcopy(base_w),deepcopy(base_r)
        samples=[]
        w,r=clone(); r["inputs"]["task"].pop("context"); samples.append(("missing-input",w,r,"WORKFLOW_INPUT_INVALID"))
        w,r=clone(); r["inputs"]["task"]=None; samples.append(("null-input",w,r,"WORKFLOW_INPUT_INVALID"))
        w,r=clone(); w["graph"]["nodes"][0]["typeId"]="vendor.unknown"; samples.append(("unknown-node",w,r,"NODE_UNRESOLVED"))
        w,r=clone(); w["graph"]["nodes"][0]["typeVersion"]="99.0.0"; samples.append(("node-version",w,r,"NODE_UNRESOLVED"))
        w,r=clone(); w["graph"]["nodes"][2]["adapter"]["capabilityId"]="different"; samples.append(("capability",w,r,"ADAPTER_CAPABILITY_MISMATCH"))
        w,r=clone(); w["futureCoreField"]={"keep":[1,None]}; samples.append(("future-field",w,r,"SCHEMA_INVALID"))
        w,r=clone(); w["schemaVersion"]="9.0.0"; samples.append(("future-schema",w,r,"SCHEMA_INVALID"))
        w,r=clone(); w["graph"]["nodes"][2]["config"]["temperature"]=.5; samples.append(("provider-parameter",w,r,"CAPABILITY_PARAMETER_INVALID"))
        w,r=clone(); w["graph"]["edges"][0]["to"]={"node":"modelA","port":"prompt"}; samples.append(("connection-type",w,r,"PORT_TYPE_MISMATCH"))
        w,r=clone(); w["graph"]["nodes"][2]["policy"]["cache"]="pure"; samples.append(("unsupported-cache",w,r,"CACHE_UNIMPLEMENTED"))
        w,r=clone(); w["graph"]["nodes"][2]["policy"]["onFailure"]="error-port"; samples.append(("unsupported-error-branch",w,r,"ERROR_BRANCH_UNIMPLEMENTED"))
        w,r=clone(); r["workflowRevision"]="different-r2"; samples.append(("run-version",w,r,"RUN_VERSION_MISMATCH"))
        w,r=clone(); r["inputs"]["task"]["context"]=[{"resourceUri":"workspace:source/../secret"}]; samples.append(("resource-traversal",w,r,"RESOURCE_TRAVERSAL"))
        for label,w,r,code in samples:
            directory=self.dir/label; directory.mkdir()
            write(directory/"workflow.json",w); write(directory/"request.json",r)
            system=SyntheticSystem(directory/"synthetic-system.sqlite"); registry=MockRegistry(system)
            try:
                with self.assertRaises(ContractError) as error: Contracts(w,r,cat,VALIDATOR,registry)
                self.eq(error.exception.code,code,label+" diagnostic")
                self.eq(system.dump()["calls"],[],label+" has zero dispatch")
                write(directory/"diagnostic.json",{"code":error.exception.code,"message":str(error.exception),"preservedJSON":read(directory/"workflow.json")==w})
            finally: system.close()
        env=read(FIX/"environment.json"); env["credentials"]["secret:effect"]["status"]="unbound"
        w,r,c=inputs("effect")
        with self.assertRaises(ContractError) as error: Session(self.dir/"no-credential",VALIDATOR,workflow=w,request=r,catalog_path=c,environment=env)
        self.eq(error.exception.code,"MOCK_CREDENTIAL_UNBOUND","missing even mock credential blocks execution")
        w,r,c=inputs("effect"); w["graph"]["nodes"][1]["policy"].update(retryMode="safe",maxAttempts=2)
        system=SyntheticSystem(self.dir/"unsafe-retry.sqlite")
        try:
            with self.assertRaises(ContractError) as error: Contracts(w,r,c,VALIDATOR,MockRegistry(system))
            self.eq(error.exception.code,"UNSAFE_RETRY","write cannot request blind retries")
        finally: system.close()

    async def test_policy_timeout_budget_priority_and_rejections(self):
        timed=self.session("serial",label="timeout",plan={"B":{"delay":.05}},
                           change=lambda w,r:w["graph"]["nodes"][1]["policy"].update(timeoutMs=1))
        st=await self.run_to(timed)
        self.eq(st["nodes"]["main/B"]["error"]["code"],"NODE_TIMEOUT","actual node deadline")
        budget=self.session("a",label="token-budget",change=lambda w,r:w["executionPolicy"]["budget"].update(maxTokens=1))
        st=await self.run_to(budget)
        self.eq(st["state"],"failed","insufficient reservation fails before model dispatch")
        self.eq(len(self.calls(budget,"main/modelA")),0,"no invocation beyond declared token budget")
        def priorities(w,r):
            w["executionPolicy"]["concurrencyLimit"]=1
            w["graph"]["nodes"][1]["policy"]["priority"]=-1
            w["graph"]["nodes"][2]["policy"]["priority"]=10
        ordered=self.session("parallel",label="priority",change=priorities)
        await self.run_to(ordered)
        b,c=self.calls(ordered,"main/B")[0],self.calls(ordered,"main/C")[0]
        self.eq(c["finished"]<=b["started"],True,"higher-priority ready task gets scarce slot")

class EvidenceResult(unittest.TextTestResult):
    records=[]
    def startTest(self,test):
        self.started=time.monotonic(); super().startTest(test)
    def addSuccess(self,test):
        self.records.append({"test":test.id(),"status":"passed","seconds":time.monotonic()-self.started}); super().addSuccess(test)
    def addFailure(self,test,err):
        self.records.append({"test":test.id(),"status":"failed","traceback":"".join(traceback.format_exception(*err))}); super().addFailure(test,err)
    def addError(self,test,err):
        self.records.append({"test":test.id(),"status":"error","traceback":"".join(traceback.format_exception(*err))}); super().addError(test,err)

def main():
    global EVIDENCE,VALIDATOR
    generate()
    EVIDENCE=HERE/"evidence"/("suite-"+datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")); EVIDENCE.mkdir(parents=True)
    VALIDATOR=SchemaClient(ROOT/"research/02-node-contracts/schemas/contract.schema.json",FIX/"catalog.json")
    with (EVIDENCE/"unittest.log").open("w",encoding="utf-8") as log:
        try:
            runner=unittest.TextTestRunner(stream=log,verbosity=2,resultclass=EvidenceResult)
            result=runner.run(unittest.defaultTestLoader.loadTestsFromTestCase(RuntimeTests))
        finally: VALIDATOR.close()
    manifest={"date":"2026-10-24","host":sys.platform,"python":sys.version,"sqlite":sqlite3.sqlite_version,
              "powershell":VALIDATOR.version,"testsRun":result.testsRun,"failures":len(result.failures),"errors":len(result.errors),
              "tests":EvidenceResult.records,"scope":"real execution of synthetic adapters only",
              "externalModelCalls":0,"realMCPConnections":0,"realAgentTasks":0,"LinuxRuns":0,"macOSRuns":0}
    write(EVIDENCE/"summary.json",manifest)
    hashes={str(p.relative_to(ROOT)).replace("\\","/"):hashlib.sha256(p.read_bytes()).hexdigest() for p in [
        ROOT/"research/02-node-contracts/schemas/contract.schema.json",BASE/"fixture-catalog.json",*sorted(HERE.glob("*.py")),HERE/"schema_host.ps1"]}
    write(EVIDENCE/"source-hashes.json",hashes)
    write(HERE/"evidence/latest.json",{"directory":str(EVIDENCE.relative_to(HERE)).replace("\\","/"),"summary":manifest})
    print(json.dumps({"evidence":str(EVIDENCE),"testsRun":result.testsRun,"failures":len(result.failures),"errors":len(result.errors)},ensure_ascii=False))
    if not result.wasSuccessful():
        print((EVIDENCE/"unittest.log").read_text(encoding="utf-8")[-18000:])
    return 0 if result.wasSuccessful() else 1

if __name__=="__main__": raise SystemExit(main())

