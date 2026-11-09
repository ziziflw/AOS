"""P0-02 offline contract checks. No engine, model/tool calls, or dependency install."""
from pathlib import Path
from copy import deepcopy
from collections import Counter, defaultdict
import hashlib, json, os, platform, re, shutil, subprocess, sys, tempfile

ROOT = Path(__file__).resolve().parents[3]
EXAMPLES = ROOT / "research/02-node-contracts/examples"
SCHEMA_PATH = ROOT / "research/02-node-contracts/schemas/contract.schema.json"
OUT = Path(__file__).with_name("static-check-results.json")
load = lambda p: json.loads(p.read_text(encoding="utf-8"))
schema = load(SCHEMA_PATH)
catalog = load(EXAMPLES / "fixture-catalog.json")
workflows = {x["workflowId"]: x for p in sorted(EXAMPLES.glob("*.workflow.json")) for x in [load(p)]}
requests = {x["workflowId"]: x for p in sorted(EXAMPLES.glob("*.run-request.json")) for x in [load(p)]}
definitions = {(x["typeId"], x["version"]): x for x in catalog["nodeDefinitions"]}
adapters = {(x["id"], x["version"]): x for x in catalog["adapterDefinitions"]}
catalog_digest = hashlib.sha256((EXAMPLES / "fixture-catalog.json").read_bytes()).hexdigest()
results, schema_jobs = [], []
def record(name, passed, detail=""):
    results.append({"id": name, "passed": bool(passed), "detail": detail})
def job(name, document, expected=True, document_schema=None):
    schema_jobs.append({"id": name, "document": document, "schema": document_schema or schema, "expected": expected})
def embedded(s):
    return {"$schema": schema["$schema"], "$defs": {**schema["$defs"], **catalog["types"]}, **s}
def graphs(w):
    yield "main", w["graph"]
    for name, body in w["subgraphs"].items():
        yield name, body["graph"]
def cycle(nodes, links):
    succ = {n: set() for n in nodes}
    for a, b in links:
        if a in succ and b in succ:
            succ[a].add(b)
    active, done = set(), set()
    def visit(n):
        if n in active: return True
        if n in done: return False
        active.add(n)
        if any(visit(k) for k in succ[n]): return True
        active.remove(n); done.add(n)
        return False
    return any(visit(n) for n in succ)
def semantic(w, cat=None):
    cat = cat or catalog
    nds = {(x["typeId"], x["version"]): x for x in cat["nodeDefinitions"]}
    ads = {(x["id"], x["version"]): x for x in cat["adapterDefinitions"]}
    errors = []
    def err(code, scope, item): errors.append({"code": code, "scope": scope, "item": item})
    def secret_fields(value):
        if isinstance(value, dict):
            return any(re.fullmatch(r"api[_-]?key|authorization|password|access[_-]?token", k, re.I)
                       or secret_fields(v) for k, v in value.items())
        return isinstance(value, list) and any(secret_fields(v) for v in value)
    if secret_fields(w): err("SECRET_FIELD_FORBIDDEN", "workflow", w["workflowId"])
    if w["catalogLock"]["sha256"] != catalog_digest: err("CATALOG_LOCK_MISMATCH", "workflow", w["workflowId"])
    reqs = {r["slot"]: r for r in w["environmentRequirements"]}
    if len(reqs) != len(w["environmentRequirements"]): err("DUPLICATE_REQUIREMENT", "workflow", "")
    calls = []
    for scope, graph in graphs(w):
        ns = {n["id"]: n for n in graph["nodes"]}
        if len(ns) != len(graph["nodes"]): err("DUPLICATE_NODE", scope, "")
        if len({e["id"] for e in graph["edges"]}) != len(graph["edges"]): err("DUPLICATE_EDGE", scope, "")
        ports, incoming = {}, defaultdict(list)
        for n in graph["nodes"]:
            d = nds.get((n["typeId"], n["typeVersion"]))
            if not d:
                err("NODE_UNRESOLVED", scope, n["id"]); continue
            ports[n["id"]] = {p["id"]: p for p in d["ports"]}
            if len(ports[n["id"]]) != len(d["ports"]): err("DUPLICATE_PORT", scope, n["id"])
            aid = n.get("adapter", {})
            ad = ads.get((aid.get("id"), aid.get("version")))
            if d["executionKind"] in ("model", "tool", "agent"):
                if not ad or ad["kind"] != d["executionKind"]:
                    err("ADAPTER_UNRESOLVED", scope, n["id"])
                elif aid["capabilityId"] != ad["capability"]["id"]:
                    err("CAPABILITY_MISMATCH", scope, n["id"])
                req = reqs.get(n.get("serviceSlot"))
                if not req or req.get("adapter") != aid: err("BINDING_REQUIREMENT_MISMATCH", scope, n["id"])
            elif aid:
                err("UNEXPECTED_ADAPTER", scope, n["id"])
            effect = d["effect"]
            if ad and ad["effect"] in ("write", "unknown"): effect = ad["effect"]
            p = n["policy"]
            if p["maxAttempts"] > 1:
                if p["retryMode"] == "safe" and (effect not in ("none", "read") or (ad and ad["capability"]["retrySafety"] != "safe-read")):
                    err("UNSAFE_RETRY", scope, n["id"])
                if p["retryMode"] == "idempotent" and (not ad or ad["capability"]["retrySafety"] != "idempotency-key"):
                    err("IDEMPOTENCY_UNAVAILABLE", scope, n["id"])
            if n["typeId"] == "core.bounded-loop":
                body = n["config"].get("bodyRef")
                if body not in w["subgraphs"]: err("SUBGRAPH_MISSING", scope, n["id"])
                calls.append((scope, body))
        for e in graph["edges"]:
            a, b = e["from"], e["to"]
            if a["node"] not in ns or b["node"] not in ns:
                err("EDGE_NODE_MISSING", scope, e["id"]); continue
            if not ns[a["node"]]["enabled"]:
                err("DISABLED_REQUIRED_SOURCE", scope, e["id"])
            pa, pb = ports.get(a["node"], {}).get(a["port"]), ports.get(b["node"], {}).get(b["port"])
            if not pa or not pb:
                err("PORT_UNRESOLVED", scope, e["id"]); continue
            if pa["direction"] != "output" or pb["direction"] != "input": err("PORT_DIRECTION", scope, e["id"])
            if pa["channel"] != e["kind"] or pb["channel"] != e["kind"]: err("EDGE_CHANNEL", scope, e["id"])
            ta, tb = pa["type"], pb["type"]
            if ta["name"] != tb["name"] or ta.get("schemaRef") != tb.get("schemaRef") or (ta["nullable"] and not tb["nullable"]):
                err("PORT_TYPE_MISMATCH", scope, e["id"])
            if pa["cardinality"] == "many" and pb["cardinality"] == "one": err("CARDINALITY_MISMATCH", scope, e["id"])
            incoming[(b["node"], b["port"])].append(e)
        for n in graph["nodes"]:
            for p in ports.get(n["id"], {}).values():
                if p["direction"] != "input": continue
                es = incoming[(n["id"], p["id"])]
                if n["enabled"] and p["required"] and not es: err("REQUIRED_INPUT_MISSING", scope, n["id"] + ":" + p["id"])
                if p["cardinality"] == "one" and len(es) > 1: err("MULTIPLE_SINGLE_INPUT", scope, n["id"] + ":" + p["id"])
                if p["cardinality"] == "many" and es:
                    orders = [e.get("order") for e in es]
                    if None in orders or len(set(orders)) != len(orders): err("ORDER_AMBIGUOUS", scope, n["id"] + ":" + p["id"])
        if cycle(ns, [(e["from"]["node"], e["to"]["node"]) for e in graph["edges"]]): err("GRAPH_CYCLE", scope, "")
    if cycle(["main", *w["subgraphs"]], calls): err("RECURSIVE_SUBGRAPH", "workflow", "")
    return errors

def preflight(w, env):
    """Declarative profile comparison only; no filesystem, credentials or network probe."""
    codes = set()
    for r in w["environmentRequirements"]:
        slot = r["slot"]
        if r["kind"] == "resource":
            if slot not in env["resources"]: codes.add("PRE_RESOURCE_UNBOUND")
            continue
        service = env["services"].get(slot)
        if not service: codes.add("PRE_SERVICE_MISSING"); continue
        if service["adapter"] != r["adapter"]: codes.add("PRE_ADAPTER_MISMATCH")
        ad = adapters.get((r["adapter"]["id"], r["adapter"]["version"]))
        if not ad: codes.add("PRE_ADAPTER_MISSING"); continue
        if not any(p["os"] == env["platform"]["os"] and p["arch"] == env["platform"]["arch"] for p in ad["platforms"]):
            codes.add("PRE_OS_ARCH_UNSUPPORTED")
        if service["target"] != ad["capability"]["selector"]: codes.add("PRE_TARGET_CHANGED")
        if service["connectionRef"] not in env["connections"]: codes.add("PRE_CONNECTION_UNBOUND")
        cred = env["credentials"].get(service["credentialRef"])
        if not cred or cred["status"] != "configured": codes.add("PRE_CREDENTIAL_MISSING")
    codes.add("PRE_RUNTIME_UNVERIFIED")
    return sorted(codes)

def portable(value):
    if isinstance(value, str):
        return not bool(re.search(r"^[A-Za-z]:[\\/]|^\\\\|^/|^file:", value))
    if isinstance(value, dict):
        return all(portable(v) for k, v in value.items() if k not in ("$schema", "$id", "inputPath", "pointer", "untilPointer"))
    if isinstance(value, list): return all(portable(v) for v in value)
    return True

def uri_safe(value):
    if isinstance(value, dict):
        for k, v in value.items():
            if k == "resourceUri" and (not re.fullmatch(r"(workspace|artifact|input):[A-Za-z0-9][A-Za-z0-9._/-]*", v)
                or ".." in v.split(":",1)[1].split("/") or "\\" in v or "%" in v):
                return False
            if not uri_safe(v): return False
    elif isinstance(value, list): return all(uri_safe(v) for v in value)
    return True

def downstream(graph, start):
    seen, todo = set(), list(start)
    while todo:
        n = todo.pop()
        for e in graph["edges"]:
            if e["from"]["node"] == n and e["to"]["node"] not in seen:
                seen.add(e["to"]["node"]); todo.append(e["to"]["node"])
    return sorted(seen)

for path in sorted(EXAMPLES.glob("*.json")):
    job("schema.document." + path.name, load(path))
for wid, w in workflows.items():
    record("semantic." + wid, not semantic(w), json.dumps(semantic(w), ensure_ascii=False))
    record("portable." + wid, portable(w))
    record("uri." + wid, uri_safe(w))
    job("input." + wid, requests[wid]["inputs"], document_schema=embedded(w["inputSchema"]))
    for scope, g in graphs(w):
        for n in g["nodes"]:
            d = definitions[(n["typeId"], n["typeVersion"])]
            job("config." + wid + "." + scope + "." + n["id"], n["config"], document_schema=embedded(d["configSchema"]))
            if "adapter" in n:
                ad = adapters[(n["adapter"]["id"], n["adapter"]["version"])]
                job("capability." + wid + "." + scope + "." + n["id"], n["config"], document_schema=embedded(ad["capability"]["parameterSchema"]))

a, b, c = [workflows["scenario-"+v] for v in "abc"]
bad = deepcopy(a); del bad["version"]["revision"]; job("negative.missing-revision", bad, False)
bad = deepcopy(a); bad["schemaVersion"] = "9.0.0"; job("negative.unsupported-schema-version", bad, False)
bad = deepcopy(a); bad["apiKey"] = "FAKE-KEY"; job("negative.root-plaintext-key", bad, False)
bad = deepcopy(a); bad["unknownCoreField"] = {"opaque": [1, None]}; job("negative.unknown-core-field", bad, False)
record("preservation.unknown-core-json-value", json.loads(json.dumps(bad, ensure_ascii=False)) == bad, "Raw JSON value round trip only; not a GUI serializer.")
bad = deepcopy(a); bad["graph"]["nodes"][0]["typeId"] = "vendor.future-node"
job("positive.unknown-node-structure", bad)
record("preservation.unknown-node-json-value", json.loads(json.dumps(bad, ensure_ascii=False)) == bad)
record("negative.unknown-node-execution-block", any(e["code"] == "NODE_UNRESOLVED" for e in semantic(bad)))
bad = deepcopy(a); bad["extensions"]["vendor:opaque"] = {"future": [1, {"x": None}]}
job("positive.namespaced-extension", bad)
record("preservation.namespaced-extension", json.loads(json.dumps(bad))["extensions"] == bad["extensions"])
bad = deepcopy(a); bad["graph"]["nodes"][0]["policy"].update(maxAttempts=2, retryMode="never")
job("negative.never-retry-multiple-attempts", bad, False)
bad = deepcopy(c); bad["graph"]["nodes"][5]["config"]["maxIterations"] = 0
job("negative.zero-loop-limit", bad["graph"]["nodes"][5]["config"], False, embedded(definitions[("core.bounded-loop","0.1.0")]["configSchema"]))
job("negative.required-node-config", {}, False, embedded(definitions[("model.generate","0.1.0")]["configSchema"]))
job("negative.provider-a-temperature", {"maxOutputTokens":512,"temperature":0.4}, False, embedded(adapters[("fixture.model.a","0.1.0")]["capability"]["parameterSchema"]))
job("positive.provider-b-temperature", {"maxOutputTokens":512,"temperature":0.4}, True, embedded(adapters[("fixture.model.b","0.1.0")]["capability"]["parameterSchema"]))
job("negative.provider-b-range", {"maxOutputTokens":512,"temperature":3}, False, embedded(adapters[("fixture.model.b","0.1.0")]["capability"]["parameterSchema"]))
job("negative.input-required-field", {"task":{"objective":"x"}}, False, embedded(a["inputSchema"]))
job("negative.null-nonnullable", {"task":None}, False, embedded(a["inputSchema"]))
job("negative.file-absolute-path", {"resourceUri":"C:\\data\\x","mediaType":"text/plain","sizeBytes":1}, False, embedded({"$ref":"#/$defs/FileReference"}))
job("negative.text-not-string", {"text":1}, False, {"type":"string"})
usage={"availability":"unknown","inputTokens":None,"outputTokens":None,"costMinor":None,"currency":None,"priceSnapshot":None}
candidate={"answer":"fixture answer","provider":"fixture","usage":usage}
comparison={"review":{"conclusion":"fixture review","findings":[]},"candidates":{"candidates":[candidate,candidate]}}
file_ref={"resourceUri":"artifact:reports/result.txt","mediaType":"text/plain","sizeBytes":12}
tool_result={"items":[{"text":"fixture result","source":file_ref}],"operationState":"confirmed"}
validation={"valid":True,"issues":[],"result":{"artifact":file_ref,"operationId":"fixture-operation","effectState":"confirmed"}}
for wid,value in zip(("scenario-a","scenario-b","scenario-c"),(comparison,tool_result,validation)):
    job("output."+wid,value,True,embedded(workflows[wid]["outputSchema"]))
bad_output=deepcopy(comparison); bad_output["candidates"]["candidates"][0]={"answer":123}
job("negative.output-structured-type",bad_output,False,embedded(a["outputSchema"]))
envelope={"kind":"value-envelope","schemaVersion":"0.1.0-draft.1","valueType":{"name":"JSON","schemaRef":"Validation","nullable":False},"payload":validation,
          "validity":"validated","provenance":{"workflowId":"scenario-c","workflowRevision":"scenario-c-r1","nodeId":"validate",
          "nodeTypeVersion":"0.1.0","attemptId":"attempt-1","logicalOperationId":"operation-1","iterationPath":[]}}
job("output.envelope-structure",envelope)
job("output.envelope-payload",envelope["payload"],True,embedded({"$ref":"#/$defs/Validation"}))
bad_envelope=deepcopy(envelope); bad_envelope["valueType"]={"name":"Text","nullable":False}; bad_envelope["payload"]=7
job("negative.envelope-text-type",bad_envelope,False)
nullable_envelope=deepcopy(envelope); nullable_envelope["valueType"]={"name":"Text","nullable":True}; nullable_envelope["payload"]=None
job("positive.envelope-nullable",nullable_envelope)
nonnullable_envelope=deepcopy(nullable_envelope); nonnullable_envelope["valueType"]["nullable"]=False
job("negative.envelope-null-nonnullable",nonnullable_envelope,False)
job("negative.tool-args-required",{"query":"x"},False,embedded({"$ref":"#/$defs/ToolArgs"}))
job("negative.tool-output-type",{"items":"not-an-array","operationState":"confirmed"},False,embedded({"$ref":"#/$defs/ToolResult"}))
job("negative.file-size",{"resourceUri":"artifact:x","mediaType":"text/plain","sizeBytes":-1},False,embedded({"$ref":"#/$defs/FileReference"}))
job("positive.nullable-json",None,True,{"type":["object","null"]})
bad=deepcopy(a); bad["extensions"]["vendor:config"]={"apiKey":"FAKE-KEY"}
record("negative.secret-field-extension",any(e["code"]=="SECRET_FIELD_FORBIDDEN" for e in semantic(bad)),"Known secret-like fields only; does not prove arbitrary free text contains no secret.")

semantic_mutations = []
x=deepcopy(a); x["graph"]["edges"][0]["to"]["port"]="prompt"; semantic_mutations.append(("wrong-port",x,"PORT_UNRESOLVED"))
x=deepcopy(a); x["graph"]["edges"][0]["to"]={"node":"modelA","port":"prompt"}; semantic_mutations.append(("wrong-type",x,"PORT_TYPE_MISMATCH"))
x=deepcopy(a); x["graph"]["edges"].pop(0); semantic_mutations.append(("missing-input",x,"REQUIRED_INPUT_MISSING"))
x=deepcopy(a); x["graph"]["nodes"][2]["typeVersion"]="99.0.0"; semantic_mutations.append(("node-version",x,"NODE_UNRESOLVED"))
x=deepcopy(a); x["catalogLock"]["sha256"]="0"*64; semantic_mutations.append(("adapter-catalog-change",x,"CATALOG_LOCK_MISMATCH"))
x=deepcopy(a); x["graph"]["edges"][4]["order"]=0; semantic_mutations.append(("join-order",x,"ORDER_AMBIGUOUS"))
x=deepcopy(a); x["graph"]["edges"][6]["kind"]="data"; semantic_mutations.append(("control-data",x,"EDGE_CHANNEL"))
x=deepcopy(a); x["graph"]["nodes"][1]["enabled"]=False; semantic_mutations.append(("disabled-source",x,"DISABLED_REQUIRED_SOURCE"))
x=deepcopy(c); x["graph"]["nodes"][2]["policy"].update(maxAttempts=2,retryMode="safe"); semantic_mutations.append(("write-blind-retry",x,"UNSAFE_RETRY"))
x=deepcopy(c); x["graph"]["nodes"][5]["config"]["bodyRef"]="missing"; semantic_mutations.append(("missing-subgraph",x,"SUBGRAPH_MISSING"))
x=deepcopy(a); x["graph"]["edges"].append({"id":"cycle","kind":"control","from":{"node":"package","port":"done"},"to":{"node":"task","port":"ready"}}); semantic_mutations.append(("cycle",x,"GRAPH_CYCLE"))
for name, document, code in semantic_mutations:
    record("negative.semantic."+name, code in [e["code"] for e in semantic(document)])
changed_catalog=deepcopy(catalog)
for definition in changed_catalog["nodeDefinitions"]:
    if definition["typeId"]=="core.task-to-text":
        next(p for p in definition["ports"] if p["id"]=="out")["type"]["nullable"]=True
record("negative.nullability-connection", any(e["code"]=="PORT_TYPE_MISMATCH" for e in semantic(a,changed_catalog)))
changed_catalog=deepcopy(catalog)
for definition in changed_catalog["nodeDefinitions"]:
    if definition["typeId"]=="core.task-to-text":
        next(p for p in definition["ports"] if p["id"]=="out")["cardinality"]="many"
record("negative.cardinality-connection", any(e["code"]=="CARDINALITY_MISMATCH" for e in semantic(a,changed_catalog)))
record("uri.path-traversal", not uri_safe({"resourceUri":"workspace:source/../secret"}))
record("uri.encoded-traversal", not uri_safe({"resourceUri":"workspace:source/%2e%2e/secret"}))
for osname in ("windows","linux"):
    env=load(EXAMPLES/("environment."+osname+".template.json"))
    for wid,w in workflows.items():
        codes=preflight(w,env)
        record("preflight."+osname+"."+wid, "PRE_CREDENTIAL_MISSING" in codes and "PRE_RUNTIME_UNVERIFIED" in codes,
               "Declarative fixture comparison: "+",".join(codes))
env=load(EXAMPLES/"environment.windows.template.json")
env["credentials"]={k:{**v,"status":"configured"} for k,v in env["credentials"].items()}
record("preflight.credentials-configured-not-proof", preflight(a,env)==["PRE_RUNTIME_UNVERIFIED"])
x=deepcopy(env); del x["services"]["model.primary"]
record("preflight.service-missing", "PRE_SERVICE_MISSING" in preflight(a,x))
x=deepcopy(env); x["platform"]["os"]="macos"
record("preflight.macos-adapter-block", "PRE_OS_ARCH_UNSUPPORTED" in preflight(a,x))
x=deepcopy(env); x["services"]["model.primary"]["target"]["model"]="silently-upgraded"
record("preflight.target-change", "PRE_TARGET_CHANGED" in preflight(a,x))
record("impact.model-a", downstream(a["graph"],["modelA"])==["join","output","package","review"])
imports={"A1":["A2","B1","C1","E2"],"A2":["B1","E1"],"B1":[],"C1":["B1","D1","D2","D3","E1","E2","E3"],
         "D1":["B1","E2","E3"],"D2":["B1","E2","E3"],"D3":["B1","E2","E3"],"E1":[],"E2":["E1"],"E3":["E1","E2"]}
record("architecture.proposed-import-dag", not cycle(imports,[(a,b) for a,bs in imports.items() for b in bs]),
       "Design dependency map only; there are no application modules to inspect.")
record("architecture.cycle-negative-control", cycle(["a","b"],[("a","b"),("b","a")]))
record("schema.local-reference-only", all(not re.search(r'"\$ref"\s*:\s*"(?!#)',json.dumps(s)) for s in [schema,catalog,*workflows.values()]),
       "Remote $ref resolution forbidden in these authored fixtures.")

pwsh=shutil.which("pwsh")
if not pwsh: raise SystemExit("Existing PowerShell with Test-Json is required; no dependency is installed.")
ps = r'''
$payload = Get-Content -LiteralPath $env:AOS_CHECK_INPUT -Raw | ConvertFrom-Json -AsHashtable -Depth 100
$checks = foreach ($check in $payload) {
  $validationErrors = @()
  $valid = Test-Json -Json ($check.document | ConvertTo-Json -Depth 100 -Compress) -Schema ($check.schema | ConvertTo-Json -Depth 100 -Compress) -ErrorAction SilentlyContinue -ErrorVariable validationErrors
  @{ id=$check.id; valid=[bool]$valid; errorCount=$validationErrors.Count }
}
@{version=$PSVersionTable.PSVersion.ToString(); os=$PSVersionTable.OS; checks=@($checks)} | ConvertTo-Json -Depth 10 -Compress
'''
with tempfile.TemporaryDirectory(prefix="aos-contract-check-") as temp_dir:
    payload_path = Path(temp_dir) / "schema-jobs.json"
    payload_path.write_text(json.dumps(schema_jobs,ensure_ascii=False),encoding="utf-8")
    run = subprocess.run([pwsh,"-NoLogo","-NoProfile","-Command",ps],
                         env={**os.environ,"AOS_CHECK_INPUT":str(payload_path)},
                         capture_output=True,text=True,encoding="utf-8",timeout=60)
if run.returncode: raise SystemExit(run.stderr)
answer=json.loads(run.stdout.lstrip("\ufeff"))
answers={r["id"]:r for r in answer["checks"]}
if len(answers) != len(schema_jobs):
    raise SystemExit("Validator result mismatch: " + json.dumps(answer, ensure_ascii=False)[:1800])
for j in schema_jobs:
    actual=answers[j["id"]]
    record(j["id"], actual["valid"]==j["expected"],
           "expected="+str(j["expected"])+" actual="+str(actual["valid"])+" validatorErrors="+str(actual["errorCount"]))
report={"date":"2026-10-24","stage":"P0-02","scope":"offline schema and limited declarative semantics only",
        "python":platform.python_version(),"powershell":answer["version"],"hostOS":answer["os"],"machine":platform.machine(),
        "dependenciesInstalled":False,"realModelCalls":0,"mcpConnections":0,"agentTasks":0,
        "linuxRuntimeTests":0,"macOSRuntimeTests":0,
        "catalogSHA256":catalog_digest,"schemaSHA256":hashlib.sha256(SCHEMA_PATH.read_bytes()).hexdigest(),
        "passed":sum(r["passed"] for r in results),"failed":sum(not r["passed"] for r in results),
        "artifactHashes":{str(p.relative_to(ROOT)).replace("\\","/"):hashlib.sha256(p.read_bytes()).hexdigest()
                          for p in [SCHEMA_PATH,Path(__file__),*sorted(EXAMPLES.glob("*.json"))]},
        "checks":results}
OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({k:v for k,v in report.items() if k not in ("checks","artifactHashes")},ensure_ascii=False))
for r in results:
    if not r["passed"]: print("FAILED "+r["id"]+" "+r["detail"])
sys.exit(1 if report["failed"] else 0)

