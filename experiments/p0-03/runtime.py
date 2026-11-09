"""Minimal C1 controller. Only this class writes authoritative execution state."""
import asyncio, time, uuid
from copy import deepcopy
from common import VERSION, TERMINAL, ContractError, OutcomeError, digest, error_value, pointer
from mocks import Context, Result

class Runtime:
    def __init__(self,contract,store,registry,environment,*,approval_ttl=300,cancel_grace=.05):
        self.c,self.store,self.registry=contract,store,registry
        self._tasks,self._cancels={},{}; self._wake=asyncio.Event(); self._driving=False
        self.ttl,self.cancel_grace=approval_ttl,cancel_grace
        self.environment=deepcopy(environment)
        self._validate_environment()
        identity={"workflow":digest(self.c.w),"request":digest(self.c.request),"catalog":self.c.w["catalogLock"]["sha256"],
                  "environment":digest(environment),"simulationPlan":digest(registry.plan)}
        old=store.load()
        if old:
            if old["identity"]!=identity: raise ContractError("RECOVERY_DEFINITION_MISMATCH")
            self._state=old
            # Never repeat an unconfirmed dispatch. Loop containers resume persisted child scopes.
            for key,n in list(old["nodes"].items()):
                if n["state"] in ("running","cancel-requested") and self.spec(key)["typeId"]!="core.bounded-loop":
                    self._recover_inflight(key)
            self._event("recovered",identity=identity)
        else:
            self._state={"recordVersion":"p0-03.1","runId":"run-"+uuid.uuid4().hex,"identity":identity,
                         "workflowId":self.c.w["workflowId"],"workflowRevision":self.c.w["version"]["revision"],
                         "seq":0,"state":"queued","cancelRequested":False,"nodes":{},"scopes":{},
                         "approvals":{},"usage":{"spentTokens":0,"reservedTokens":0,"costMinor":0},
                         "createdAt":time.time()}
            initial=deepcopy(self._state)
            self._add_scope(initial,"main","main",self.c.request["inputs"],[],None)
            self._state=self.store.commit(initial,{"kind":"run-created","runId":initial["runId"],"identity":identity})
    @property
    def snapshot(self): return deepcopy(self._state)
    def _recover_inflight(self,key):
        # Default remains conservative. A trusted C1 subclass may only resume a verified query.
        self._terminal(key,"unknown",error={"code":"INTERRUPTED_IN_FLIGHT","message":"No durable result confirmation",
                                            "category":"unknown","retryable":False,"sideEffect":"unknown"})
    def _validate_environment(self):
        e=self.environment; self.c.v.validate(e)
        if e["profileId"]!=self.c.request["environmentProfile"]: raise ContractError("ENVIRONMENT_PROFILE_MISMATCH")
        if e["platform"]!={"os":"windows","arch":"x64"}: raise ContractError("TARGET_NOT_VERIFIED")
        for r in self.c.w["environmentRequirements"]:
            if r["kind"]=="resource":
                if r["slot"] not in e["resources"]: raise ContractError("RESOURCE_REQUIREMENT_MISSING")
                if e["resources"][r["slot"]]["mountPath"]!="memory:synthetic": raise ContractError("REAL_RESOURCE_FORBIDDEN")
            else:
                b=e["services"].get(r["slot"])
                if not b or b["adapter"]!=r.get("adapter"): raise ContractError("SERVICE_BINDING_MISMATCH")
                ad=self.c.adapters[(b["adapter"]["id"],b["adapter"]["version"])]
                if b["target"]!=ad["capability"]["selector"]: raise ContractError("CAPABILITY_TARGET_CHANGED")
                cred=e["credentials"].get(b["credentialRef"])
                if not cred or cred["status"]!="configured" or not cred["vaultAlias"].startswith("mock:"):
                    raise ContractError("MOCK_CREDENTIAL_UNBOUND")
                con=e["connections"].get(b["connectionRef"])
                if not con or con!={"transport":"cli","programRef":"builtin:mock","environmentRefs":[]}:
                    raise ContractError("EXTERNAL_CONNECTION_FORBIDDEN")
    def _change(self,kind,fn=None,**details):
        candidate=deepcopy(self._state)
        if fn: fn(candidate)
        self._state=self.store.commit(candidate,{"kind":kind,"runId":candidate["runId"],**details})
        self._wake.set()
    def _event(self,kind,**details): self._change(kind,**details)
    def _transition(self,key,state,phase=None,**values):
        old=self._state["nodes"][key]["state"]
        allowed={"queued":{"running","skipped","cancelled","failed","waiting-approval"},
                 "waiting-approval":{"queued","failed","cancelled"},
                 "running":{"succeeded","failed","unknown","cancel-requested","cancelled"},
                 "cancel-requested":{"cancelled","unknown"},"failed":{"queued"}}
        if state!=old and state not in allowed.get(old,set()): raise ContractError("ILLEGAL_STATE_TRANSITION",(key,old,state))
        def update(s):
            n=s["nodes"][key]; n["state"]=state
            if phase: n["phase"]=phase
            n.update(deepcopy(values))
        self._change("node-transition",update,key=key,old=old,state=state,phase=phase,values=values)
    def _run_state(self,state):
        if self._state["state"]!=state: self._change("run-transition",lambda s:s.update(state=state),state=state)
    def spec(self,key):
        n=self._state["nodes"][key]; scope=self._state["scopes"][n["scope"]]
        return next(x for x in self.c.graphs[scope["graphRef"]]["nodes"] if x["id"]==n["nodeId"])
    def _add_scope(self,state,scope,graph_ref,inputs,iteration,parent):
        sub=self.c.w if graph_ref=="main" else self.c.w["subgraphs"][graph_ref]
        self.c.v.validate(inputs,sub["inputSchema"],"SUBGRAPH_INPUT_INVALID")
        state["scopes"][scope]={"graphRef":graph_ref,"inputs":deepcopy(inputs),"iteration":iteration,"parent":parent,"state":"running"}
        for node in self.c.graphs[graph_ref]["nodes"]:
            key=scope+"/"+node["id"]
            state["nodes"][key]={"nodeId":node["id"],"scope":scope,"state":"queued","phase":"waiting-dependencies",
                                 "attempts":[],"outputs":{},"operationId":"op-"+digest([state["runId"],scope,node["id"]])[:32]}
    def _dependencies(self,key):
        record=self._state["nodes"][key]; scope=record["scope"]; node=self.spec(key)
        graph=self.c.graphs[self._state["scopes"][scope]["graphRef"]]
        edges=[e for e in graph["edges"] if e["to"]["node"]==node["id"]]
        sources=[self._state["nodes"][scope+"/"+e["from"]["node"]] for e in edges]
        if any(n["state"] not in TERMINAL for n in sources): return "wait",{}
        if any(n["state"] in ("failed","unknown","cancelled") for n in sources): return "blocked",{}
        active, inactive=[],[]
        for e,n in zip(edges,sources):
            (active if n["state"]=="succeeded" and e["from"]["port"] in n["outputs"] else inactive).append(e)
        exclusive=node["typeId"] in ("core.merge-exclusive","synth.merge-exclusive")
        if inactive and not exclusive: return "skip",{}
        values={}
        for port in self.c.ports(node).values():
            if port["direction"]!="input": continue
            pe=[e for e in active if e["to"]["port"]==port["id"]]
            if port["cardinality"]=="many": pe.sort(key=lambda e:e["order"])
            if port["required"] and not pe:
                if exclusive: raise OutcomeError("EXCLUSIVE_JOIN_COUNT")
                return "skip",{}
            if pe:
                data=[deepcopy(self._state["nodes"][scope+"/"+e["from"]["node"]]["outputs"][e["from"]["port"]]["payload"]) for e in pe]
                for v in data: self.c.value(v,port)
                values[port["id"]]=data if port["cardinality"]=="many" else data[0]
        if exclusive and len(values.get("items",[]))!=1: raise OutcomeError("EXCLUSIVE_JOIN_COUNT")
        return "ready",values
    def _fingerprint(self,key,inputs):
        return digest({"runId":self._state["runId"],"identity":self._state["identity"],"key":key,
                       "operationId":self._state["nodes"][key]["operationId"],"spec":self.spec(key),"inputs":inputs})
    def _gate(self,key,inputs):
        node=self.spec(key)
        required=self.c.effect(node) in ("write","unknown") or node["policy"]["approval"]=="always" or self.c.w["executionPolicy"]["approval"]=="always" or node["typeId"]=="core.approval"
        if not required: return True
        fp=self._fingerprint(key,inputs)
        record=self._state["nodes"][key]
        a=self._state["approvals"].get(record.get("approvalId"))
        if a and a["status"]=="granted" and a["fingerprint"]==fp and a["expiresAt"]>time.time():
            return True
        if a and a["status"]=="pending" and a["fingerprint"]==fp and a["expiresAt"]>time.time():
            return False
        approval_id="approval-"+digest([fp,self._state["seq"]+1])[:24]
        def request(s):
            if a: s["approvals"][a["id"]]["status"]="revoked"
            s["approvals"][approval_id]={"id":approval_id,"key":key,"fingerprint":fp,"status":"pending","expiresAt":time.time()+self.ttl}
            s["nodes"][key].update(state="waiting-approval",phase="waiting-approval",approvalId=approval_id)
        self._change("approval-requested",request,key=key,approvalId=approval_id,fingerprint=fp)
        return False
    def approve(self,approval_id,fingerprint,decision=True):
        a=self._state["approvals"].get(approval_id)
        if not a or a["fingerprint"]!=fingerprint: raise ContractError("APPROVAL_CONTENT_MISMATCH")
        if self._state["cancelRequested"] or self._state["state"] in TERMINAL: raise ContractError("APPROVAL_RUN_INACTIVE")
        if a["status"] in ("granted","consumed"): return a["status"]
        if a["status"]!="pending": raise ContractError("APPROVAL_INACTIVE")
        if a["expiresAt"]<=time.time():
            self._change("approval-expired",lambda s:s["approvals"][approval_id].update(status="revoked"),key=a["key"])
            raise ContractError("APPROVAL_EXPIRED")
        _,inputs=self._dependencies(a["key"])
        if self._fingerprint(a["key"],inputs)!=fingerprint: raise ContractError("APPROVAL_CONTENT_CHANGED")
        def resolve(s):
            s["approvals"][approval_id]["status"]="granted" if decision else "denied"
            s["nodes"][a["key"]].update(state="queued" if decision else "failed",phase="ready" if decision else "denied")
            if not decision: s["nodes"][a["key"]]["error"]={"code":"APPROVAL_DENIED","message":"Trusted controller rejected operation","category":"permission","retryable":False,"sideEffect":"not-started"}
        self._change("approval-resolved",resolve,key=a["key"],approvalId=approval_id,decision=decision)
        return "granted" if decision else "denied"
    def _reserve(self,key):
        node=self.spec(key); amount=node["config"].get("maxOutputTokens",0)
        usage=self._state["usage"]
        limit=self.c.w["executionPolicy"]["budget"].get("maxTokens")
        local=node["policy"]["budget"].get("maxTokens")
        if (local is not None and amount>local) or (limit is not None and usage["spentTokens"]+usage["reservedTokens"]+amount>limit):
            raise OutcomeError("TOKEN_BUDGET_EXCEEDED")
        return amount
    def _begin(self,key,inputs):
        node=self.spec(key); record=self._state["nodes"][key]
        attempt_id="attempt-"+digest([self._state["runId"],key,len(record["attempts"])+1])[:24]
        reserved=self._reserve(key)
        a=self._state["approvals"].get(record.get("approvalId"))
        def begin(s):
            n=s["nodes"][key]; n.update(state="running",phase="running",startedAt=time.time())
            n["attempts"].append({"id":attempt_id,"number":len(n["attempts"])+1,"state":"running",
                                  "inputs":deepcopy(inputs),"reservedTokens":reserved,"startedAt":time.time()})
            s["usage"]["reservedTokens"]+=reserved
            if a:
                if a["status"]!="granted" or a["fingerprint"]!=self._fingerprint(key,inputs) or a["expiresAt"]<=time.time():
                    raise ContractError("APPROVAL_NOT_VALID")
                s["approvals"][a["id"]]["status"]="consumed"
        self._change("node-dispatched",begin,key=key,attemptId=attempt_id,operationId=record["operationId"])
        return attempt_id
    def _envelopes(self,key,outputs,attempt_id):
        node=self.spec(key); ports=self.c.ports(node); record=self._state["nodes"][key]
        selected=set(outputs)
        allowed={p["id"] for p in ports.values() if p["direction"]=="output" and p["channel"]=="data"}-{"error","rejected"}
        t=node["typeId"]
        if t in ("core.condition","synth.condition"):
            if len(selected)!=1 or not selected<=allowed: raise ContractError("CONDITIONAL_OUTPUT_INVALID")
        else:
            required=allowed
            if selected!=required: raise ContractError("OUTPUT_SET_MISMATCH",(selected,required))
        outputs={**outputs,"done":{"state":"succeeded","sequence":self._state["seq"]+1,"attemptId":attempt_id}}
        result={}
        for name,value in outputs.items():
            port=ports[name]; self.c.value(value,port)
            provenance={"workflowId":self.c.w["workflowId"],"workflowRevision":self.c.w["version"]["revision"],
                        "nodeId":node["id"],"nodeTypeVersion":node["typeVersion"],"attemptId":attempt_id,
                        "logicalOperationId":record["operationId"],"iterationPath":self._state["scopes"][record["scope"]]["iteration"]}
            if "adapter" in node: provenance.update(adapterVersion=node["adapter"]["version"],capabilityId=node["adapter"]["capabilityId"])
            envelope={"kind":"value-envelope","schemaVersion":VERSION,"valueType":port["type"],"payload":deepcopy(value),
                      "validity":"validated","provenance":provenance,"contentDigest":digest(value)}
            self.c.v.validate(envelope)
            result[name]=envelope
        return result
    def _terminal(self,key,state,*,outputs=None,result=None,error=None,usage_tokens=0,usage_cost=0):
        current=self._state["nodes"][key]
        def finish(s):
            n=s["nodes"][key]; n.update(state=state,phase=state)
            if outputs is not None: n["outputs"]=deepcopy(outputs)
            if result is not None: n["result"]=deepcopy(result)
            if error is not None: n["error"]=deepcopy(error)
            if n["attempts"]:
                a=n["attempts"][-1]
                if a["state"] in ("running","cancel-requested"):
                    s["usage"]["reservedTokens"]-=a["reservedTokens"]
                    a.update(state=state,finishedAt=time.time(),usageTokens=usage_tokens)
                    if error: a["error"]=deepcopy(error)
            s["usage"]["spentTokens"]+=usage_tokens; s["usage"]["costMinor"]+=usage_cost
        self._change("node-terminal",finish,key=key,old=current["state"],state=state,
                     attemptId=current["attempts"][-1]["id"] if current["attempts"] else None,error=error)
    async def _execute(self,key,inputs,attempt_id):
        node=self.spec(key); record=self._state["nodes"][key]
        cancel=self._cancels[key]
        ctx=Context(key,deepcopy(node),deepcopy(inputs),deepcopy(self._state["scopes"][record["scope"]]["inputs"]),
                    list(self._state["scopes"][record["scope"]]["iteration"]),attempt_id,len(record["attempts"]),record["operationId"],cancel)
        try:
            # All registered handlers here are cooperative Python mocks; this is not a remote-kill guarantee.
            out=await asyncio.wait_for(self.registry.invoke(ctx),node["policy"]["timeoutMs"]/1000)
            now=self._state["nodes"][key]
            if now["state"] in TERMINAL:
                self._event("late-result-discarded",key=key,attemptId=attempt_id); return
            if self._state["cancelRequested"] or now["state"]=="cancel-requested":
                self._terminal(key,"unknown" if self.c.effect(node) in ("write","unknown") else "cancelled",
                               error=error_value(OutcomeError("CANCELLED_RESULT_DISCARDED",side_effect="unknown" if self.c.effect(node) in ("write","unknown") else "not-started")))
                return
            env=self._envelopes(key,out.outputs,attempt_id)
            if node["typeId"].startswith(("core.output.","synth.output")):
                schema=self.c.w["outputSchema"] if record["scope"]=="main" else self.c.w["subgraphs"][self._state["scopes"][record["scope"]]["graphRef"]]["outputSchema"]
                self.c.v.validate(out.result,schema,"WORKFLOW_OUTPUT_INVALID")
            self._validate_usage(key,out)
            self._terminal(key,"succeeded",outputs=env,result=out.result,usage_tokens=out.usage_tokens,usage_cost=out.usage_cost)
        except asyncio.CancelledError:
            if self._state["nodes"][key]["state"] not in TERMINAL:
                self._terminal(key,"unknown" if self.c.effect(node) in ("write","unknown") else "cancelled",
                               error=error_value(OutcomeError("COOPERATIVE_CANCEL",side_effect="unknown" if self.c.effect(node) in ("write","unknown") else "not-started")))
        except Exception as exc:
            if self._state["nodes"][key]["state"] in TERMINAL:
                self._event("late-error-discarded",key=key,attemptId=attempt_id); return
            if isinstance(exc,TimeoutError):
                exc=OutcomeError("NODE_TIMEOUT",retryable=self.c.effect(node) in ("none","read"),
                                 side_effect="unknown" if self.c.effect(node) in ("write","unknown","billable") else "not-started")
            unknown=getattr(exc,"side_effect",None)=="unknown"
            self._terminal(key,"unknown" if unknown else "failed",error=error_value(exc))
            attempts=len(self._state["nodes"][key]["attempts"])
            if not unknown and not self._state["cancelRequested"] and getattr(exc,"retryable",False) and node["policy"]["retryMode"]=="safe" and self.c.effect(node) in ("none","read") and attempts<node["policy"]["maxAttempts"]:
                self._transition(key,"queued","ready",error=None)
        finally:
            self._tasks.pop(key,None); self._cancels.pop(key,None); self._wake.set()
    def _validate_usage(self,key,out):
        """Legacy synthetic accounting; trusted profiles may validate richer SDK usage."""
        node=self.spec(key);now=self._state["nodes"][key]
        if type(out.usage_tokens) is not int or type(out.usage_cost) is not int or min(out.usage_tokens,out.usage_cost)<0:
            raise ContractError("ADAPTER_USAGE_INVALID")
        if out.usage_cost != 0: raise ContractError("NONZERO_SYNTHETIC_COST_FORBIDDEN")
        if out.usage_tokens>node["config"].get("maxOutputTokens",out.usage_tokens): raise ContractError("ADAPTER_TOKEN_LIMIT_BREACH")
        local=node["policy"]["budget"].get("maxTokens")
        local_spent=sum(a.get("usageTokens",0) for a in now["attempts"])
        if local is not None and local_spent+out.usage_tokens>local: raise ContractError("TOKEN_BUDGET_EXCEEDED")
    def _loop_progress(self,key):
        n=self._state["nodes"][key]; cfg=self.spec(key)["config"]
        loop=n.get("loop")
        if not loop:
            _,inputs=self._dependencies(key)
            loop={"iteration":0,"feedback":inputs["in"],"child":None}
        child=loop.get("child")
        if child:
            scope=self._state["scopes"][child]
            if scope["state"]=="running": return False
            if scope["state"]!="succeeded":
                self._terminal(key,"unknown" if scope["state"]=="unknown" else "failed",error=error_value(OutcomeError("LOOP_CHILD_"+scope["state"].upper(),side_effect="unknown" if scope["state"]=="unknown" else "not-started"))); return True
            value=scope["result"]
            if pointer(value,cfg["untilPointer"])==cfg["untilEquals"]:
                attempt=n["attempts"][-1]["id"]
                self._terminal(key,"succeeded",outputs=self._envelopes(key,{"out":value},attempt)); return True
            loop={**loop,"iteration":loop["iteration"]+1,"feedback":value,"child":None}
        if loop["iteration"]>=cfg["maxIterations"]:
            self._terminal(key,"failed",error=error_value(OutcomeError("LOOP_LIMIT_EXCEEDED"))); return True
        child=key+"/iteration-"+str(loop["iteration"])
        loop={**loop,"child":child}
        iteration=self._state["scopes"][n["scope"]]["iteration"]+[loop["iteration"]]
        def create(s):
            s["nodes"][key]["loop"]=deepcopy(loop)
            self._add_scope(s,child,cfg["bodyRef"],{"feedback":loop["feedback"]},iteration,key)
        self._change("iteration-created",create,key=key,scope=child,iterationPath=iteration)
        return True
    def _scopes_progress(self):
        changed=False
        for scope_id,scope in list(self._state["scopes"].items()):
            if scope["state"]!="running": continue
            nodes={k:v for k,v in self._state["nodes"].items() if v["scope"]==scope_id}
            if not all(n["state"] in TERMINAL for n in nodes.values()): continue
            statuses={n["state"] for n in nodes.values()}
            sink=next(v for k,v in nodes.items() if self.spec(k)["typeId"].startswith(("core.output.","synth.output")))
            state="unknown" if "unknown" in statuses else "failed" if "failed" in statuses else "cancelled" if "cancelled" in statuses else "succeeded" if sink["state"]=="succeeded" else "skipped"
            def update(s,scope_id=scope_id,state=state,sink=sink):
                s["scopes"][scope_id].update(state=state,result=deepcopy(sink.get("result")))
            self._change("scope-terminal",update,scope=scope_id,state=state)
            changed=True
        return changed
    def cancel(self):
        if self._state["state"] in TERMINAL: return
        self._change("run-cancel-requested",lambda s:s.update(cancelRequested=True))
        self._run_state("cancel-requested")
        self._change("approvals-revoked",lambda s:[a.update(status="revoked") for a in s["approvals"].values() if a["status"] in ("pending","granted")])
        self._cancel_nodes()
    def cancel_node(self,key):
        n=self._state["nodes"][key]
        if n["state"] in TERMINAL: return
        if self.spec(key)["typeId"]=="core.bounded-loop": raise ContractError("USE_RUN_CANCEL_FOR_CONTAINER")
        aid=n.get("approvalId")
        if aid: self._change("approval-revoked",lambda s:s["approvals"][aid].update(status="revoked"),key=key)
        if n["state"] in ("queued","waiting-approval"): self._transition(key,"cancelled","cancelled")
        elif n["state"]=="running":
            self._transition(key,"cancel-requested","cancel-requested",cancelAt=time.time())
            if key in self._cancels: self._cancels[key].set()
    def _cancel_nodes(self):
        for key,n in list(self._state["nodes"].items()):
            if n["state"] in TERMINAL: continue
            if n["state"] in ("queued","waiting-approval"):
                self._transition(key,"cancelled","cancelled")
            elif n["state"]=="running":
                self._transition(key,"cancel-requested","cancel-requested",cancelAt=time.time())
                if key in self._cancels: self._cancels[key].set()
            elif n["state"]=="cancel-requested":
                if self.spec(key)["typeId"]=="core.bounded-loop":
                    children=[v for k,v in self._state["scopes"].items() if v["parent"]==key]
                    if all(v["state"]!="running" for v in children): self._terminal(key,"cancelled")
                elif time.time()-n["cancelAt"]>=self.cancel_grace:
                    self._terminal(key,"unknown",error=error_value(OutcomeError("CANCEL_UNCONFIRMED",side_effect="unknown")))
    def _advance(self):
        changed=True
        while changed:
            changed=False
            if self._state["cancelRequested"]: self._cancel_nodes()
            for key,n in list(self._state["nodes"].items()):
                if n["state"]=="cancel-requested" and key in self._tasks and time.time()-n["cancelAt"]>=self.cancel_grace:
                    self._terminal(key,"unknown",error=error_value(OutcomeError("CANCEL_UNCONFIRMED",side_effect="unknown")))
            changed=self._scopes_progress() or changed
            for key,n in list(self._state["nodes"].items()):
                if n["state"]=="running" and self.spec(key)["typeId"]=="core.bounded-loop":
                    if time.time()-n["startedAt"]>self.spec(key)["policy"]["timeoutMs"]/1000:
                        self.cancel(); return
                    changed=self._loop_progress(key) or changed
            if self._state["cancelRequested"]: break
            candidates=[]
            for key,n in list(self._state["nodes"].items()):
                if n["state"] not in ("queued","waiting-approval"): continue
                node=self.spec(key)
                if not node["enabled"]:
                    self._transition(key,"skipped","disabled"); changed=True; continue
                try: status,inputs=self._dependencies(key)
                except Exception as exc:
                    self._terminal(key,"failed",error=error_value(exc)); changed=True; continue
                if status in ("blocked","skip"):
                    self._transition(key,"skipped","dependency-"+status); changed=True; continue
                if status=="ready":
                    if n["phase"]=="waiting-dependencies":
                        self._change("node-ready",lambda s,key=key:s["nodes"][key].update(phase="ready"),key=key); changed=True
                    if not self._gate(key,inputs): continue
                    candidates.append((key,inputs))
            candidates.sort(key=lambda x:(-self.spec(x[0])["policy"]["priority"],x[0]))
            for key,inputs in candidates:
                node=self.spec(key)
                # Container nodes don't occupy worker slots, avoiding child-scope deadlock.
                group=node.get("adapter",{}).get("id",node["typeId"])
                peers=[self.spec(k) for k in self._tasks if self.spec(k).get("adapter",{}).get("id",self.spec(k)["typeId"])==group]
                group_limit=min([node["policy"]["concurrencyLimit"],*[p["policy"]["concurrencyLimit"] for p in peers]])
                if node["typeId"]!="core.bounded-loop" and (len(self._tasks)>=self.c.w["executionPolicy"]["concurrencyLimit"] or len(peers)>=group_limit):
                    continue
                try: attempt=self._begin(key,inputs)
                except OutcomeError as exc:
                    self._terminal(key,"failed",error=error_value(exc)); changed=True; continue
                if node["typeId"]!="core.bounded-loop":
                    self._cancels[key]=asyncio.Event()
                    self._tasks[key]=asyncio.create_task(self._execute(key,inputs,attempt))
                changed=True
        self._scopes_progress()
        main=self._state["scopes"]["main"]
        if main["state"]!="running": self._run_state(main["state"])
    async def drive(self):
        if self._driving: raise ContractError("CONTROLLER_DRIVE_REENTRY")
        self._driving=True
        try:
            if self._state["state"] in TERMINAL: return self.snapshot
            if not self._state["cancelRequested"]: self._run_state("running")
            while True:
                self._wake.clear(); self._advance()
                if self._state["state"] in TERMINAL: return self.snapshot
                if time.time()-self._state["createdAt"]>self.c.w["executionPolicy"]["timeoutMs"]/1000:
                    self.cancel()
                if not self._tasks:
                    if any(n["state"]=="waiting-approval" for n in self._state["nodes"].values()):
                        self._run_state("waiting-approval"); return self.snapshot
                    # One extra pass resolves freshly completed container/scopes.
                    before=self._state["seq"]; self._advance()
                    if self._state["state"] in TERMINAL: return self.snapshot
                    if self._state["seq"]==before:
                        self._event("deadlock-diagnosed")
                        self._run_state("failed"); return self.snapshot
                    continue
                wake=asyncio.create_task(self._wake.wait())
                await asyncio.wait([*self._tasks.values(),wake],timeout=.01,return_when=asyncio.FIRST_COMPLETED)
                if not wake.done(): wake.cancel()
                await asyncio.gather(wake,return_exceptions=True)
        finally: self._driving=False
    async def close(self):
        # Cleanup only trusted in-process mock tasks, never claimed to kill a blocking external call.
        if self._tasks:
            self.cancel()
            for task in list(self._tasks.values()): task.cancel()
        self.registry.release.set()
        if self._tasks:
            await asyncio.gather(*list(self._tasks.values()),return_exceptions=True)

