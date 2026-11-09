"""Fixed per-protocol capability schemas in the existing P0-02 catalog format."""
import hashlib,importlib.util
from copy import deepcopy
from boot import HERE,ROOT,read,write,ContractError
from fixtures import policy,port,node,edge,obj
spec=importlib.util.spec_from_file_location('p007_profile_source',HERE.parent/'p0-07/workbench_profile.py')
old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
CATALOG=HERE/'fixtures/catalog.json'
MODES=['text','large','slow','json','badjson','rate','error','delay','lost','missing','secret','leak']
MODELS={}
for provider in ('openai','anthropic'):
    for structured in (False,True):
        tid='p08.'+provider+('.json' if structured else '.text')
        MODELS[tid]={'provider':provider,'structured':structured,'apiVersion':'v1-chat-completions' if provider=='openai' else '2023-06-01',
           'inputModalities':['text'],'toolCalling':False,'streaming':False,'reasoning':False,'remoteCancellation':False,'synthetic':True}
LABELS={**old.LABELS,**{tid:('OpenAI' if c['provider']=='openai' else 'Anthropic')+' SDK · 离线 '+('JSON' if c['structured'] else '文本') for tid,c in MODELS.items()},'p08.json-text':'提取结构化答案','p08.join':'汇合文本'}
DEFAULTS=deepcopy(old.DEFAULTS)
def config_schema(tid):
    cap=MODELS[tid];provider=cap['provider']
    props={'model':{'title':'固定离线模型 / 故障夹具','enum':['fixture-'+m for m in MODES]},
      'credentialAlias':{'title':'环境凭据别名','const':'credential:fixture'},
      'maxInputTokens':{'title':'输入准入上限（合成）','type':'integer','minimum':128,'maximum':2048},
      'maxOutputTokens':{'title':'最大输出 Token','type':'integer','minimum':8,'maximum':1024},
      'maxCallCostMinor':{'title':'单次费用预留（合成分）','type':'integer','minimum':1,'maximum':100}}
    # Distinct, verified fixture capabilities. No claim that all Anthropic models lack temperature.
    if provider=='openai':props['temperature']={'type':'number','minimum':0,'maximum':2,'title':'温度（离线协议字段）'}
    return obj(props)
for tid in MODELS:
    DEFAULTS[tid]={'model':'fixture-json' if MODELS[tid]['structured'] else 'fixture-text','credentialAlias':'credential:fixture',
      'maxInputTokens':512,'maxOutputTokens':64,'maxCallCostMinor':10,**({'temperature':.4} if MODELS[tid]['provider']=='openai' else {})}
def adapter(tid):return {'id':'fixture.'+tid,'version':'0.1.0','capabilityId':'cap.fixture.'+tid}
def build_catalog():
    c=old.build_catalog();template=read(ROOT/'research/02-node-contracts/examples/fixture-catalog.json')['adapterDefinitions'][0]
    controls=deepcopy(c['nodeDefinitions'][0]['ports'][-3:]);c['types']['P08Answer']=obj({'answer':{'type':'string'}})
    for tid,cap in MODELS.items():
        cfg=config_schema(tid);out=port('out','output','JSON',ref='P08Answer') if cap['structured'] else port('out','output')
        c['nodeDefinitions'].append({'typeId':tid,'version':'0.1.0','executionKind':'model','ports':[port('in','input'),out]+deepcopy(controls),
          'configSchema':cfg,'effect':'billable','supportedControls':list(policy())})
        a=deepcopy(template);a.update(id=adapter(tid)['id'],kind='model',effect='billable')
        a['capability'].update(id=adapter(tid)['capabilityId'],observedAt='2026-10-29',selector={'provider':'fixture-'+cap['provider'],'model':tid,'apiVersion':cap['apiVersion'],'interface':'generate'},parameterSchema=cfg,retrySafety='never')
        a['platforms']=[p for p in a['platforms'] if p['os']=='windows']
        for p in a['platforms']:
            p['minRuntime']={'name':'python','version':'3.12.14'};p['protocol']={'name':'http-json-fixture','version':cap['apiVersion']}
            p['permissions']=['synthetic:model-http']
        c['adapterDefinitions'].append(a)
    c['nodeDefinitions'].append({'typeId':'p08.json-text','version':'0.1.0','executionKind':'builtin',
      'ports':[port('in','input','JSON',ref='P08Answer'),port('out','output')]+deepcopy(controls),'configSchema':obj({}),'effect':'none','supportedControls':list(policy())})
    c['nodeDefinitions'].append({'typeId':'p08.join','version':'0.1.0','executionKind':'builtin',
      'ports':[port('items','input',many=True),port('out','output')]+deepcopy(controls),'configSchema':obj({}),'effect':'none','supportedControls':list(policy())})
    return c
def requirements(nodes):
    rs=old.requirements(nodes)
    for tid in MODELS:
        if any(n['typeId']==tid for n in nodes):rs.append({'slot':tid,'kind':'service','required':True,'adapter':adapter(tid),'permissions':['synthetic:model-http']})
    return rs
def make_node(tid,id):
    n=old.make_node(tid,id)
    if tid in MODELS:n.update(config=deepcopy(DEFAULTS[tid]),adapter=adapter(tid),serviceSlot=tid)
    return n
def sample(tid='p08.openai.text',mode=None):
    if tid is True:return old.sample(True)
    if tid is False:tid='p08.openai.text'
    ids=['text','model']+(['extract'] if MODELS[tid]['structured'] else [])+['output']
    tids=['synth.source',tid]+(['p08.json-text'] if MODELS[tid]['structured'] else [])+['synth.output']
    nodes=[make_node(t,i) for t,i in zip(tids,ids)]
    if mode:nodes[1]['config']['model']='fixture-'+mode
    w=old.sample()['workflow'];w.update(workflowId='p08-model-workbench',title='SDK 模型 · 离线 HTTP 验证',graph={'nodes':nodes,'edges':[edge(ids[i],ids[i+1],index=i) for i in range(len(ids)-1)]},environmentRequirements=requirements(nodes))
    w['catalogLock']['sha256']=hashlib.sha256(CATALOG.read_bytes()).hexdigest()
    return {'workflow':w,'layout':{'version':'aos-layout/0.1','positions':{id:{'x':i*280,'y':60} for i,id in enumerate(ids)}}}
def environment():
    e=old.environment()
    # Existing P0-05 convention: bind a trusted local program, resolve its ephemeral HTTP endpoint at runtime.
    e['connections']['connection:p08-model']={'transport':'cli','programRef':'program:aos-p08-executor','environmentRefs':[]}
    e['credentials']['secret:p08-model']={'vaultAlias':'aos:p08:owned-fixture','status':'configured'}
    c=read(CATALOG)
    for tid in MODELS:
        ad=next(a for a in c['adapterDefinitions'] if a['id']==adapter(tid)['id'])
        e['services'][tid]={'serviceRef':'service:'+tid,'connectionRef':'connection:p08-model','credentialRef':'secret:p08-model',
          'adapter':adapter(tid),'target':deepcopy(ad['capability']['selector'])}
    return e
def request(w):return old.request(w)
if __name__=='__main__':
    CATALOG.parent.mkdir(exist_ok=True);write(CATALOG,build_catalog())
    for tid in MODELS:write(HERE/'fixtures'/(tid+'.document.json'),sample(tid))
    write(HERE/'fixtures/capabilities.json',MODELS)
