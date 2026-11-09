"""P0-02 schema validation and conservative execution-plan validation."""
from collections import defaultdict
from copy import deepcopy
from pathlib import Path
import hashlib, json, queue, shutil, subprocess, threading
from common import ContractError, check_references, digest, dumps, read

class SchemaClient:
    """Existing local PowerShell/JsonSchema.NET, never a replacement schema dialect."""
    def __init__(self, schema_path, catalog_path):
        self.schema = read(schema_path)
        pwsh = shutil.which("pwsh")
        if not pwsh: raise ContractError("VALIDATOR_UNAVAILABLE")
        self.process = subprocess.Popen([pwsh, "-NoLogo", "-NoProfile", "-File", str(Path(__file__).with_name("schema_host.ps1")),
                                         "-SchemaFile", str(schema_path), "-CatalogFile", str(catalog_path)],
                                        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                        encoding="utf-8", bufsize=1)
        self.replies, self.cache, self.version = queue.Queue(), {}, None
        def reader():
            for line in self.process.stdout: self.replies.put(line)
            self.replies.put(None)
        threading.Thread(target=reader, daemon=True).start()
    def validate(self, value, sub_schema=None, code="SCHEMA_INVALID"):
        check_references(value)
        if sub_schema is not None: check_references(sub_schema, schema=True)
        key = digest([value, sub_schema])
        if key not in self.cache:
            self.process.stdin.write(dumps({"value": value, **({"schema": sub_schema} if sub_schema is not None else {})})+"\n")
            self.process.stdin.flush()
            try: line = self.replies.get(timeout=15)
            except queue.Empty:
                self.close(); raise ContractError("VALIDATOR_TIMEOUT")
            if line is None: raise ContractError("VALIDATOR_CLOSED")
            reply = json.loads(line.lstrip("\ufeff")); self.version = reply["version"]
            self.cache[key] = reply
        result = self.cache[key]
        if not result["valid"]: raise ContractError(code, result["errors"][:3])
    def close(self):
        if self.process.poll() is None:
            self.process.stdin.close()
            try: self.process.wait(timeout=2)
            except subprocess.TimeoutExpired: self.process.kill(); self.process.wait()
        self.process.stdout.close(); self.process.stderr.close()

class Contracts:
    def __init__(self, workflow, request, catalog_path, validator, registry):
        self.w, self.request = deepcopy(workflow), deepcopy(request)
        self.catalog_path, self.v, self.registry = Path(catalog_path), validator, registry
        self.v.validate(self.w); self.v.validate(self.request)
        self.catalog = read(catalog_path)
        self.defs = {(d["typeId"],d["version"]):d for d in self.catalog["nodeDefinitions"]}
        self.adapters = {(d["id"],d["version"]):d for d in self.catalog["adapterDefinitions"]}
        self.graphs = {"main": self.w["graph"], **{k:v["graph"] for k,v in self.w["subgraphs"].items()}}
        self.order = {}
        self.validate()
    def definition(self, node):
        try: return self.defs[(node["typeId"],node["typeVersion"])]
        except KeyError: raise ContractError("NODE_UNRESOLVED", node["id"])
    def ports(self, node):
        return {p["id"]:p for p in self.definition(node)["ports"]}
    def effect(self, node):
        rank = {"none":0, "read":1, "billable":2, "write":3, "unknown":4}
        effects = [self.definition(node)["effect"], self.registry.metadata(node["typeId"])["effect"]]
        if "adapter" in node: effects.append(self.adapters[(node["adapter"]["id"],node["adapter"]["version"])]["effect"])
        return max(effects, key=rank.get)
    def value(self, value, port):
        t = port["type"]
        if value is None:
            if not t["nullable"]: raise ContractError("NULL_NOT_ALLOWED", port["id"])
            return
        name = t["name"]
        if name == "Text": sub = {"type":"string"}
        elif name == "JSON":
            if t["schemaRef"] not in self.catalog["types"]: raise ContractError("TYPE_UNREGISTERED", t["schemaRef"])
            sub = {"$ref":"#/$defs/"+t["schemaRef"]}
        elif name in ("FileReference","MediaReference","Error","ExecutionStatus"): sub={"$ref":"#/$defs/"+name}
        else: raise ContractError("TYPE_UNREGISTERED", name)
        self.v.validate(value, sub, "PORT_VALUE_INVALID")
    def validate(self):
        for document in (self.catalog, self.w, self.request): self.v.validate(document)
        if self.w["catalogLock"]["sha256"] != hashlib.sha256(self.catalog_path.read_bytes()).hexdigest():
            raise ContractError("CATALOG_LOCK_MISMATCH")
        if (self.request["workflowId"],self.request["workflowRevision"]) != (self.w["workflowId"],self.w["version"]["revision"]):
            raise ContractError("RUN_VERSION_MISMATCH")
        self.v.validate(self.request["inputs"], self.w["inputSchema"], "WORKFLOW_INPUT_INVALID")
        if len(self.defs)!=len(self.catalog["nodeDefinitions"]) or len(self.adapters)!=len(self.catalog["adapterDefinitions"]):
            raise ContractError("DUPLICATE_REGISTRY_ENTRY")
        if set(self.catalog["types"]) & set(self.v.schema["$defs"]): raise ContractError("TYPE_SHADOWS_CORE")
        reqs = {r["slot"]:r for r in self.w["environmentRequirements"]}
        if len(reqs)!=len(self.w["environmentRequirements"]): raise ContractError("DUPLICATE_REQUIREMENT")
        self.check_policy(self.w["executionPolicy"], workflow=True)
        calls = defaultdict(set)
        for name,g in self.graphs.items():
            ns = {n["id"]:n for n in g["nodes"]}
            if len(ns)!=len(g["nodes"]) or len({e["id"] for e in g["edges"]})!=len(g["edges"]):
                raise ContractError("DUPLICATE_GRAPH_ID", name)
            incoming, successors = defaultdict(list), {n:set() for n in ns}
            for n in ns.values():
                d=self.definition(n)
                self.registry.metadata(n["typeId"])  # allowlisted implementation, not a descriptor alone
                if n["typeVersion"] != "0.1.0": raise ContractError("IMPLEMENTATION_VERSION_MISMATCH")
                ps=self.ports(n)
                if len(ps)!=len(d["ports"]): raise ContractError("DUPLICATE_PORT")
                self.v.validate(n["config"],d["configSchema"],"CONFIG_INVALID")
                self.check_policy(n["policy"])
                if n.get("extensions"): raise ContractError("NODE_EXTENSION_UNSUPPORTED")
                if n["policy"]["retryMode"]=="idempotent": raise ContractError("IDEMPOTENT_EXECUTION_UNIMPLEMENTED")
                if n["policy"]["maxAttempts"]>1 and self.effect(n) not in ("none","read"):
                    raise ContractError("UNSAFE_RETRY")
                if "adapter" in n:
                    a=n["adapter"]; ad=self.adapters.get((a["id"],a["version"]))
                    if not ad or ad["kind"]!=d["executionKind"] or a["capabilityId"]!=ad["capability"]["id"]:
                        raise ContractError("ADAPTER_CAPABILITY_MISMATCH")
                    r=reqs.get(n.get("serviceSlot"))
                    if not r or r.get("adapter")!=a: raise ContractError("SERVICE_REQUIREMENT_MISMATCH")
                    if not a["id"].startswith("fixture."): raise ContractError("REAL_ADAPTER_FORBIDDEN")
                    self.v.validate(n["config"],ad["capability"]["parameterSchema"],"CAPABILITY_PARAMETER_INVALID")
                    if n["policy"]["maxAttempts"]>1 and ad["capability"]["retrySafety"]!="safe-read":
                        raise ContractError("UNSAFE_RETRY")
                elif d["executionKind"] in ("model","tool","agent"): raise ContractError("ADAPTER_REQUIRED")
                for p in ps.values():
                    if p["channel"]=="control" and (p["type"]["name"]!="ExecutionStatus" or p["type"]["nullable"]):
                        raise ContractError("CONTROL_TYPE_INVALID")
                    if p["type"]["name"]=="JSON" and p["type"]["schemaRef"] not in self.catalog["types"]:
                        raise ContractError("TYPE_UNREGISTERED")
                    if p["type"]["name"] not in ("Text","JSON","FileReference","MediaReference","Error","ExecutionStatus"):
                        raise ContractError("TYPE_UNREGISTERED")
                if n["typeId"]=="core.bounded-loop":
                    body=n["config"]["bodyRef"]
                    if body not in self.w["subgraphs"]: raise ContractError("SUBGRAPH_MISSING")
                    calls[name].add(body)
            for e in g["edges"]:
                try:
                    a,b=e["from"],e["to"]; pa=self.ports(ns[a["node"]])[a["port"]]; pb=self.ports(ns[b["node"]])[b["port"]]
                except KeyError: raise ContractError("EDGE_REFERENCE_INVALID", e["id"])
                if pa["direction"]!="output" or pb["direction"]!="input": raise ContractError("PORT_DIRECTION")
                if pa["channel"]!=e["kind"] or pb["channel"]!=e["kind"]: raise ContractError("EDGE_CHANNEL")
                ta,tb=pa["type"],pb["type"]
                if ta["name"]!=tb["name"] or ta.get("schemaRef")!=tb.get("schemaRef") or (ta["nullable"] and not tb["nullable"]):
                    raise ContractError("PORT_TYPE_MISMATCH")
                if pa["cardinality"]!="one": raise ContractError("MULTI_OUTPUT_UNIMPLEMENTED")
                incoming[(b["node"],b["port"])].append(e); successors[a["node"]].add(b["node"])
            for n in ns.values():
                for p in self.ports(n).values():
                    if p["direction"]!="input": continue
                    es=incoming[(n["id"],p["id"])]
                    if n["enabled"] and p["required"] and not es: raise ContractError("REQUIRED_INPUT_MISSING")
                    if p["cardinality"]=="one" and len(es)>1: raise ContractError("MULTIPLE_SINGLE_INPUT")
                    if p["cardinality"]=="many" and es and (any("order" not in e for e in es) or len({e["order"] for e in es})!=len(es)):
                        raise ContractError("ORDER_AMBIGUOUS")
            self.order[name]=self.topological(successors)
            sinks=[n for n in ns.values() if n["typeId"].startswith("core.output.") or n["typeId"].startswith("synth.output")]
            if len(sinks)!=1: raise ContractError("EXACTLY_ONE_OUTPUT_REQUIRED",name)
            # Disconnected components cannot be silently omitted.
            ancestors={sinks[0]["id"]}
            while True:
                nxt=ancestors | {e["from"]["node"] for e in g["edges"] if e["to"]["node"] in ancestors}
                if nxt==ancestors: break
                ancestors=nxt
            if ancestors!=set(ns): raise ContractError("DISCONNECTED_NODE")
        self.topological({name:set(calls[name]) for name in self.graphs})
    @staticmethod
    def topological(succ):
        result=[]; remaining={k:set(v) for k,v in succ.items()}
        while remaining:
            ready=sorted(k for k in remaining if not any(k in v for v in remaining.values()))
            if not ready: raise ContractError("GRAPH_CYCLE")
            result.extend(ready)
            for key in ready: del remaining[key]
        return result
    @staticmethod
    def check_policy(p, workflow=False):
        if p["cache"]!="off": raise ContractError("CACHE_UNIMPLEMENTED")
        if p["onFailure"]!="stop": raise ContractError("ERROR_BRANCH_UNIMPLEMENTED")
        if workflow and (p["maxAttempts"]!=1 or p["retryMode"]!="never"): raise ContractError("WORKFLOW_REPLAY_UNIMPLEMENTED")

