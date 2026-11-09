"""Fixed task/port contracts and Agent Card profile, shared declarations only."""
from bootstrap_agent import ROOT,read
from copy import deepcopy
BASE=ROOT/'research/02-node-contracts/examples'
ORIGINAL=read(BASE/'fixture-catalog.json')
CORE=read(ROOT/'research/02-node-contracts/schemas/contract.schema.json')['$defs']
def obj(properties): return {'type':'object','properties':properties,'required':list(properties),'additionalProperties':False}
MODES=['normal','reject','fail','wait-input','wait-auth','bad-result','bad-reference','wrong-identity','wrong-task','duplicate','stale-state',
       'result-delayed','result-never','cancel-unsupported','finish-after-cancel','query-drop-once','query-unavailable',
       'protocol-error','service-exit','lost-submit','bad-secret-error']
ARGS=obj({'text':{'type':'string','minLength':1,'maxLength':64},'delayMs':{'type':'integer','minimum':150,'maximum':2500},'mode':{'enum':MODES}})
RESULT=obj({'text':{'type':'string'},'agent':{'type':'string'},'taskId':{'type':'string'},'operationId':{'type':'string'},'artifact':deepcopy(CORE['FileReference'])})
RESULTS={'type':'array','items':{'$ref':'#/$defs/AgentTaskResult'},'minItems':2,'maxItems':2}
CONFIG=obj({'skill':{'enum':['echo','effect']},'pollMs':{'type':'integer','minimum':10,'maximum':100},'waitTimeoutMs':{'type':'integer','minimum':200,'maximum':10000}})
EXTENSION='https://aos.invalid/extensions/p0-05/task-profile/v1'
def card(name,base):
    return {'name':'aos-p05-'+name,'description':'Trusted synthetic independent task service','version':'0.1.0',
      'supportedInterfaces':[{'url':base+'/rpc','protocolBinding':'JSONRPC','protocolVersion':'1.0'}],
      'capabilities':{'extensions':[{'uri':EXTENSION,'description':'Synthetic schema/sequence/correlation profile; not a universal A2A guarantee','params':
          {'inputSchema':ARGS,'outputSchema':RESULT,'messageIdDeduplication':True,'correlationLookup':'contextId plus exact dispatch identity','agent':name}}]},
      'defaultInputModes':['application/json'],'defaultOutputModes':['application/json'],
      'skills':[{'id':s,'name':s,'description':'Synthetic '+s,'tags':['synthetic','deterministic'],'inputModes':['application/json'],'outputModes':['application/json']} for s in ('echo','effect')],
      'securitySchemes':{'local':{'httpAuthSecurityScheme':{'scheme':'bearer','description':'Isolated synthetic session marker only; not real account authentication'}}},
      'securityRequirements':[{'schemes':{'local':{'list':[]}}}]}
