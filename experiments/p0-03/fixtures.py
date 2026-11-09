"""Synthetic fixtures in the unchanged P0-02 JSON contract; no new workflow dialect."""
from copy import deepcopy
from pathlib import Path
import hashlib
from common import read, write
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
BASE=ROOT/"research/02-node-contracts/examples"
FIX=HERE/"fixtures"
def obj(properties,required=None):
    return {"type":"object","properties":properties,"required":list(properties) if required is None else required,"additionalProperties":False}
def port(name,direction,kind="Text",nullable=False,many=False,ref=None):
    return {"id":name,"direction":direction,"channel":"data","type":{"name":kind,"nullable":nullable,**({"schemaRef":ref} if ref else {})},
            "cardinality":"many" if many else "one","required":True}
def policy():
    return {"timeoutMs":30000,"maxAttempts":1,"retryMode":"never","concurrencyLimit":2,"priority":0,
            "budget":{"maxTokens":4096,"maxCostMinor":100,"currency":"CNY"},"onFailure":"stop","approval":"policy","cache":"off"}
def node(name,type_id,config=None):
    n={"id":name,"typeId":type_id,"typeVersion":"0.1.0","enabled":True,"config":config or {},"policy":policy()}
    if type_id=="synth.effect":
        n.update(adapter={"id":"fixture.tool.effect","version":"0.1.0","capabilityId":"cap.fixture.tool.effect"},serviceSlot="tool.effect")
    return n
def edge(a,b,*,out="out",inp="in",order=0,index=0):
    return {"id":"edge-"+str(index),"kind":"data","from":{"node":a,"port":out},"to":{"node":b,"port":inp},"order":order}
def catalog():
    c=read(BASE/"fixture-catalog.json")
    c["types"]["SynthTextList"]={"type":"array","items":{"type":"string"}}
    plain=obj({})
    ps=[
      ("synth.source",[],[port("out","output")],obj({"value":{"type":"string"}}),"none"),
      ("synth.step",[port("in","input")],[port("out","output")],obj({"suffix":{"type":"string"}}),"none"),
      ("synth.join-all",[port("items","input",many=True)],[port("out","output","JSON",ref="SynthTextList")],obj({"mode":{"const":"all"}}),"none"),
      ("synth.merge-exclusive",[port("items","input",many=True)],[port("out","output")],obj({"mode":{"const":"exactly-one-active"}}),"none"),
      ("synth.condition",[port("in","input")],[port("pass","output"),port("fail","output")],obj({"select":{"enum":["pass","fail"]}}),"none"),
      ("synth.output",[port("in","input")],[],plain,"none"),
      ("synth.output-list",[port("in","input","JSON",ref="SynthTextList")],[],plain,"none"),
      ("synth.effect",[port("in","input")],[port("out","output")],obj({"suffix":{"type":"string"}}),"write"),
      ("synth.null",[],[port("out","output",nullable=True)],plain,"none"),
      ("synth.null-step",[port("in","input",nullable=True)],[port("out","output",nullable=True)],plain,"none"),
      ("synth.output-null",[port("in","input",nullable=True)],[],plain,"none"),
      ("synth.error-value",[port("in","input")],[port("out","output")],plain,"none")
    ]
    controls=c["nodeDefinitions"][0]["ports"][-3:]
    for tid,ins,outs,cfg,effect in ps:
        c["nodeDefinitions"].append({"typeId":tid,"version":"0.1.0","executionKind":"tool" if tid=="synth.effect" else "builtin",
                                    "ports":ins+outs+deepcopy(controls),"configSchema":cfg,"effect":effect,"supportedControls":list(policy())})
    a=deepcopy(c["adapterDefinitions"][2])
    a.update(id="fixture.tool.effect",effect="write")
    a["capability"].update(id="cap.fixture.tool.effect",selector={"provider":"fixture","model":"effect","apiVersion":"synthetic-v1","interface":"tool"},
                           parameterSchema=obj({"suffix":{"type":"string"}}),retrySafety="never")
    for p in a["platforms"]: p["protocol"]={"name":"synthetic","version":"1"}
    c["adapterDefinitions"].append(a)
    return c
def workflow(name,nodes,links,output_schema):
    for i,e in enumerate(links): e["id"]="edge-"+str(i)
    requirements=[]
    if any(n["typeId"]=="synth.effect" for n in nodes):
        requirements=[{"slot":"tool.effect","kind":"service","required":True,"adapter":{"id":"fixture.tool.effect","version":"0.1.0","capabilityId":"cap.fixture.tool.effect"},"permissions":["synthetic:write"]}]
    return {"kind":"workflow","schemaVersion":"0.1.0-draft.1","workflowId":name,"version":{"revision":name+"-r1"},
            "title":"P0-03 synthetic "+name,"catalogLock":{"resourceRef":"catalog:core","sha256":hashlib.sha256((FIX/"catalog.json").read_bytes()).hexdigest()},
            "inputSchema":obj({}),"outputSchema":output_schema,"environmentRequirements":requirements,
            "graph":{"nodes":nodes,"edges":links},"subgraphs":{},"executionPolicy":policy(),"extensions":{"aos:fixture-only":True}}
def environment(c):
    e=read(BASE/"environment.windows.template.json")
    e["resources"]={"workspace:source":{"mountPath":"memory:synthetic","mode":"read"}}
    for cred in e["credentials"].values(): cred.update(status="configured",vaultAlias="mock:"+cred["vaultAlias"])
    for key in e["connections"]: e["connections"][key]={"transport":"cli","programRef":"builtin:mock","environmentRefs":[]}
    a=next(a for a in c["adapterDefinitions"] if a["id"]=="fixture.tool.effect")
    e["services"]["tool.effect"]={"serviceRef":"service:effect","connectionRef":"connection:effect","credentialRef":"secret:effect",
                                  "adapter":{"id":a["id"],"version":a["version"],"capabilityId":a["capability"]["id"]},"target":a["capability"]["selector"]}
    e["connections"]["connection:effect"]={"transport":"cli","programRef":"builtin:mock","environmentRefs":[]}
    e["credentials"]["secret:effect"]={"vaultAlias":"mock:effect","status":"configured"}
    return e
def generate():
    FIX.mkdir(exist_ok=True)
    c=catalog(); write(FIX/"catalog.json",c); write(FIX/"environment.json",environment(c))
    serial=workflow("serial",[node("A","synth.source",{"value":"seed"}),node("B","synth.step",{"suffix":"B"}),node("C","synth.output")],
                    [edge("A","B"),edge("B","C")],{"type":"string"})
    parallel=workflow("parallel",[node("A","synth.source",{"value":"seed"}),node("B","synth.step",{"suffix":"B"}),
                                  node("C","synth.step",{"suffix":"C"}),node("D","synth.join-all",{"mode":"all"}),node("out","synth.output-list")],
                      [edge("A","B"),edge("A","C"),edge("B","D",inp="items",order=0),edge("C","D",inp="items",order=1),edge("D","out")],
                      {"$ref":"#/$defs/SynthTextList"})
    conditional=workflow("conditional",[node("A","synth.source",{"value":"seed"}),node("K","synth.condition",{"select":"pass"}),
                                         node("B","synth.step",{"suffix":"B"}),node("C","synth.step",{"suffix":"C"}),
                                         node("M","synth.merge-exclusive",{"mode":"exactly-one-active"}),node("out","synth.output")],
                         [edge("A","K"),edge("K","B",out="pass"),edge("K","C",out="fail"),edge("B","M",inp="items",order=0),edge("C","M",inp="items",order=1),edge("M","out")],
                         {"type":"string"})
    all_skip=deepcopy(conditional); all_skip["workflowId"]="conditional-all"; all_skip["version"]["revision"]="conditional-all-r1"
    all_skip["graph"]["nodes"][-2].update(typeId="synth.join-all",config={"mode":"all"})
    all_skip["graph"]["nodes"][-1]["typeId"]="synth.output-list"; all_skip["outputSchema"]={"$ref":"#/$defs/SynthTextList"}
    effect=workflow("effect",[node("A","synth.source",{"value":"seed"}),node("B","synth.effect",{"suffix":"-write"}),node("C","synth.output")],
                    [edge("A","B"),edge("B","C")],{"type":"string"})
    null=workflow("nullable",[node("A","synth.null"),node("B","synth.null-step"),node("C","synth.output-null")],
                  [edge("A","B"),edge("B","C")],{"type":["string","null"]})
    error=workflow("bad-output",[node("A","synth.source",{"value":"seed"}),node("B","synth.error-value"),node("C","synth.output")],
                   [edge("A","B"),edge("B","C")],{"type":"string"})
    for w in (serial,parallel,conditional,all_skip,effect,null,error):
        write(FIX/(w["workflowId"]+".workflow.json"),w)
        write(FIX/(w["workflowId"]+".request.json"),{"kind":"run-request","schemaVersion":"0.1.0-draft.1","workflowId":w["workflowId"],
                                                   "workflowRevision":w["version"]["revision"],"environmentProfile":"fixture-windows-x64","inputs":{}})
    return c
if __name__=="__main__": generate(); print("Generated P0-02-compatible synthetic fixtures.")

