"""Shared declarations only. Engine never imports the server implementation."""
from copy import deepcopy
from bootstrap import ROOT,read,digest
catalog=read(ROOT/'research/02-node-contracts/examples/fixture-catalog.json')
core=read(ROOT/'research/02-node-contracts/schemas/contract.schema.json')['$defs']
def expand(v):
    if isinstance(v,dict):
        if '$ref' in v: return expand(({**core,**catalog['types']})[v['$ref'].split('/')[-1]])
        return {k:expand(x) for k,x in v.items()}
    if isinstance(v,list): return [expand(x) for x in v]
    return v
def obj(p): return {'type':'object','properties':p,'required':list(p),'additionalProperties':False}
text={'type':'string','maxLength':128}
SPECS={
 'echo_text':(obj({'text':text}),obj({'text':text}),'none'),
 'add_numbers':(obj({'a':{'type':'number','minimum':-1000000,'maximum':1000000},'b':{'type':'number','minimum':-1000000,'maximum':1000000}}),obj({'sum':{'type':'number'}}),'none'),
 'delayed_result':(obj({'delayMs':{'type':'integer','minimum':10,'maximum':1500},'value':text}),obj({'value':text}),'none'),
 'structured_result':(expand(catalog['types']['ToolArgs']),expand(catalog['types']['ToolResult']),'read'),
 'simulated_failure':(obj({'mode':{'enum':['tool-error','protocol-error','retry-once']}}),obj({'ok':{'type':'boolean'}}),'none'),
 'simulated_effect':(obj({'value':text}),obj({'value':text,'operationId':{'type':'string'}}),'write')}
def descriptor(name):
    ins,outs,effect=SPECS[name]
    # Deliberately misleading annotation on effect proves permission doesn't trust annotations.
    return {'name':name,'description':'AOS P0-04 trusted synthetic '+name,'inputSchema':deepcopy(ins),'outputSchema':deepcopy(outs),
            'annotations':{'readOnlyHint':True,'destructiveHint':False},'_meta':{'aos:tool-version':'0.1.0'}}
def signature(d): return digest({k:d.get(k) for k in ('name','inputSchema','outputSchema','_meta')})
