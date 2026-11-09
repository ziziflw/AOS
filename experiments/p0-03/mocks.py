"""Allowlisted in-process mocks and a separate synthetic 'external system' ledger."""
import asyncio, sqlite3, time
from copy import deepcopy
from dataclasses import dataclass
from common import ContractError, OutcomeError, pointer

@dataclass(frozen=True)
class Context:
    key: str
    node: dict
    inputs: dict
    scope_inputs: dict
    iteration: list
    attempt_id: str
    attempt_no: int
    operation_id: str
    cancel: asyncio.Event

@dataclass
class Result:
    outputs: dict
    result: object = None
    usage_tokens: int = 0
    usage_cost: int = 0

class SyntheticSystem:
    """Separate commits deliberately model non-atomic external effects, not run state."""
    def __init__(self,path):
        self.db=sqlite3.connect(path,isolation_level=None)
        self.db.execute("PRAGMA journal_mode=WAL"); self.db.execute("PRAGMA synchronous=FULL")
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS calls(attempt TEXT PRIMARY KEY,node TEXT,operation TEXT,started INTEGER,finished INTEGER);
        CREATE TABLE IF NOT EXISTS effects(operation TEXT PRIMARY KEY,node TEXT,count INTEGER);
        CREATE TABLE IF NOT EXISTS artifacts(uri TEXT PRIMARY KEY,data BLOB,media TEXT);
        """)
        self.db.execute("INSERT OR IGNORE INTO artifacts VALUES(?,?,?)",("workspace:source/sample.txt",b"sample data\n","text/plain"))
    def begin(self,ctx):
        self.db.execute("INSERT INTO calls VALUES(?,?,?,?,NULL)",(ctx.attempt_id,ctx.key,ctx.operation_id,time.perf_counter_ns()))
    def finish(self,ctx):
        self.db.execute("UPDATE calls SET finished=? WHERE attempt=?",(time.perf_counter_ns(),ctx.attempt_id))
    def effect(self,ctx):
        self.db.execute("INSERT INTO effects VALUES(?,?,1) ON CONFLICT(operation) DO UPDATE SET count=count+1",(ctx.operation_id,ctx.key))
    def put(self,uri,data):
        self.db.execute("INSERT OR REPLACE INTO artifacts VALUES(?,?,?)",(uri,data,"text/plain"))
        return {"resourceUri":uri,"mediaType":"text/plain","sizeBytes":len(data)}
    def resource(self,reference):
        from common import check_references
        import hashlib
        check_references(reference)
        row=self.db.execute("SELECT data,media FROM artifacts WHERE uri=?",(reference["resourceUri"],)).fetchone()
        if not row: raise ContractError("RESOURCE_NOT_BOUND",reference["resourceUri"])
        data,media=row
        if reference["sizeBytes"]!=len(data) or reference["mediaType"]!=media: raise ContractError("RESOURCE_METADATA_MISMATCH")
        if "sha256" in reference and hashlib.sha256(data).hexdigest()!=reference["sha256"]: raise ContractError("RESOURCE_DIGEST_MISMATCH")
        return data
    def dump(self):
        return {"calls":[dict(zip(("attempt","node","operation","started","finished"),r)) for r in self.db.execute("SELECT * FROM calls ORDER BY started")],
                "effects":[dict(zip(("operation","node","count"),r)) for r in self.db.execute("SELECT * FROM effects")],
                "artifacts":[{"uri":r[0],"size":len(r[1]),"media":r[2]} for r in self.db.execute("SELECT * FROM artifacts")]}
    def close(self): self.db.close()

class MockRegistry:
    BUILTINS={"core.input.task","core.input.tool-request","core.input.goal","core.input.feedback",
              "core.task-to-text","core.join-candidates","core.package-comparison","core.output.comparison",
              "core.map-tool-args","core.check-tool-result","core.output.tool-result","core.validate-artifact",
              "core.condition","core.bounded-loop","core.merge-exclusive","core.approval","core.output.validation",
              "model.generate","model.review","tool.query","agent.plan","agent.execute","agent.repair",
              "synth.source","synth.step","synth.join-all","synth.merge-exclusive","synth.condition","synth.output",
              "synth.output-list","synth.effect","synth.null","synth.null-step","synth.output-null","synth.error-value"}
    def __init__(self,system,plan=None):
        self.system=system; self.plan=deepcopy(plan or {}); self.barriers={}; self.release=asyncio.Event()
    def metadata(self,type_id):
        if type_id not in self.BUILTINS: raise ContractError("IMPLEMENTATION_UNAVAILABLE",type_id)
        return {"effect":"write" if type_id in ("agent.execute","agent.repair","synth.effect") else
                "read" if type_id in ("tool.query","core.validate-artifact") else
                "billable" if type_id.startswith("model.") or type_id=="agent.plan" else "none"}
    def behavior(self,ctx): return self.plan.get(ctx.key,self.plan.get(ctx.node["id"],{}))
    async def invoke(self,ctx):
        self.metadata(ctx.node["typeId"])
        self.system.begin(ctx)
        b=self.behavior(ctx)
        if b.get("barrier"):
            await self.barriers.setdefault(b["barrier"],asyncio.Barrier(2)).wait()
        if b.get("wait"):
            if b.get("cooperative",True):
                await ctx.cancel.wait(); raise asyncio.CancelledError()
            await self.release.wait()  # intentionally ignores cooperative cancellation
        await asyncio.sleep(b.get("delay",0))
        if ctx.cancel.is_set() and b.get("cooperative",True): raise asyncio.CancelledError()
        if b.get("failFirst") and ctx.attempt_no==1: raise OutcomeError("SAFE_TRANSIENT",retryable=True)
        if b.get("fail"): raise OutcomeError("SIMULATED_FAILURE")
        n=ctx.node; t=n["typeId"]; x=ctx.inputs; cfg=n["config"]
        tokens=0
        if t.startswith("core.input."): outputs={"out":deepcopy(pointer(ctx.scope_inputs,cfg["inputPath"]))}
        elif t=="core.task-to-text": outputs={"out":"\n".join([x["in"]["objective"],*x["in"]["context"]])}
        elif t=="model.generate":
            tokens=4
            outputs={"out":{"answer":n["id"]+": "+x["prompt"],"provider":n["adapter"]["id"],
                            "usage":{"availability":"reported","inputTokens":1,"outputTokens":3,"costMinor":0,"currency":"CNY","priceSnapshot":"synthetic-zero"}}}
        elif t=="model.review":
            tokens=4; outputs={"out":{"conclusion":"synthetic comparison","findings":[c["provider"] for c in x["in"]["candidates"]]}}
        elif t=="core.join-candidates":
            if len(x["items"])!=cfg["expectedCount"]: raise OutcomeError("JOIN_COUNT")
            outputs={"out":{"candidates":x["items"]}}
        elif t=="core.package-comparison": outputs={"out":{"review":x["review"],"candidates":x["candidates"]}}
        elif t=="core.map-tool-args": outputs={"out":deepcopy(x["in"])}
        elif t=="tool.query":
            self.system.resource(x["args"]["source"])
            outputs={"out":{"items":[{"text":x["args"]["query"],"source":x["args"]["source"]}],"operationState":"confirmed"}}
        elif t=="core.check-tool-result":
            if x["in"]["operationState"]!="confirmed": raise OutcomeError("TOOL_RESULT_UNKNOWN",side_effect="unknown")
            outputs={"out":deepcopy(x["in"])}
        elif t=="agent.plan":
            outputs={"out":{"steps":[x["in"]["objective"]],"scope":x["in"]["allowedScope"]}}
        elif t in ("agent.execute","agent.repair"):
            self.system.effect(ctx)
            success=t=="agent.repair" and ctx.iteration[-1]>=b.get("successAt",0)
            f=self.system.put("artifact:reports/"+ctx.operation_id+".txt",b"VALID" if success else b"INVALID")
            outputs={"out":{"artifact":f,"operationId":ctx.operation_id,"effectState":"confirmed"}}
        elif t=="core.validate-artifact":
            data=self.system.resource(x["in"]["artifact"])
            valid=data==b"VALID" and x["in"]["effectState"]=="confirmed"
            outputs={"out":{"valid":valid,"issues":[] if valid else ["synthetic review failed"],"result":x["in"]}}
        elif t=="core.condition":
            p="pass" if pointer(x["in"],cfg["pointer"])==cfg["equals"] else "fail"
            outputs={p:deepcopy(x["in"])}
        elif t=="core.merge-exclusive":
            if len(x["items"])!=1: raise OutcomeError("EXCLUSIVE_JOIN_COUNT")
            outputs={"out":x["items"][0]}
        elif t=="core.approval": outputs={"approved":deepcopy(x["in"])}
        elif t.startswith("core.output.") or t.startswith("synth.output"):
            self.system.finish(ctx); return Result({},deepcopy(x["in"]))
        elif t=="synth.source": outputs={"out":cfg["value"]}
        elif t in ("synth.step","synth.effect"):
            if t=="synth.effect": self.system.effect(ctx)
            outputs={"out":x["in"]+cfg["suffix"]}
        elif t=="synth.join-all": outputs={"out":deepcopy(x["items"])}
        elif t=="synth.merge-exclusive":
            if len(x["items"])!=1: raise OutcomeError("EXCLUSIVE_JOIN_COUNT")
            outputs={"out":x["items"][0]}
        elif t=="synth.condition": outputs={cfg["select"]:x["in"]}
        elif t=="synth.null": outputs={"out":None}
        elif t=="synth.null-step": outputs={"out":x["in"]}
        elif t=="synth.error-value": outputs={"out":{"code":"Fake","message":"error-as-data","category":"execution","retryable":False,"sideEffect":"not-started"}}
        else: raise ContractError("HANDLER_UNSUPPORTED",t)
        if b.get("lostResponse"): raise OutcomeError("RESPONSE_LOST",side_effect="unknown")
        if "outputOverride" in b: outputs=deepcopy(b["outputOverride"])
        self.system.finish(ctx)
        return Result(outputs,usage_tokens=tokens)

