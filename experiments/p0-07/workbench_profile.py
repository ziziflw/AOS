"""Fixed trusted catalog, using the unchanged P0-02 catalog/workflow format."""
from copy import deepcopy
import hashlib
from boot import HERE,ROOT,read,write,digest,ContractError
from fixtures import catalog as core_catalog,policy,port,node,edge,obj
from cases import environment as mcp_environment,FIX as MCP_FIX

CATALOG=HERE/'fixtures/catalog.json'
LABELS={'synth.source':'文本输入','synth.step':'文本处理','p07.model':'合成模型 · 模拟',
 'p07.echo-args':'封装 Echo 参数','tool.mcp.echo_text':'MCP · Echo',
 'p07.echo-text':'提取 Echo 文本','synth.output':'文本输出',
 'p07.effect-args':'封装合成写入','tool.mcp.simulated_effect':'MCP · 合成写入',
 'p07.effect-text':'提取写入结果'}
DEFAULTS={'synth.source':{'value':'设计一条可解释的工作流'},'synth.step':{'suffix':' / 已整理'},
 'p07.model':{'maxOutputTokens':128,'temperature':0.4,'delayMs':700,'fail':False},
 'tool.mcp.echo_text':{'operation':'echo_text'},'tool.mcp.simulated_effect':{'operation':'simulated_effect'}}

def build_catalog():
    original=core_catalog(); mcp=read(MCP_FIX/'catalog.json')
    c=deepcopy(original);c['nodeDefinitions']=[d for d in c['nodeDefinitions'] if d['typeId'] in LABELS]
    c['adapterDefinitions']=[]
    for name in ('echo_text','simulated_effect'):
        c['types']['MCPArgs_'+name]=mcp['types']['MCPArgs_'+name]
        c['types']['MCPResult_'+name]=mcp['types']['MCPResult_'+name]
        c['nodeDefinitions'].append(deepcopy(next(d for d in mcp['nodeDefinitions'] if d['typeId']=='tool.mcp.'+name)))
        c['adapterDefinitions'].append(deepcopy(next(d for d in mcp['adapterDefinitions'] if d['id']=='fixture.p04.'+name)))
    controls=deepcopy(original['nodeDefinitions'][0]['ports'][-3:])
    definitions=[('p07.model',[port('in','input'),port('out','output')],obj({
      'maxOutputTokens':{'title':'最大输出字符数（合成）','type':'integer','minimum':1,'maximum':4096},
      'temperature':{'title':'温度（仅验证参数，不影响合成文本）','type':'number','minimum':0,'maximum':2},
      'delayMs':{'title':'合成耗时 ms','type':'integer','minimum':0,'maximum':10000},
      'fail':{'title':'注入合成失败','type':'boolean'}}))]
    for name,stem in (('echo_text','echo'),('simulated_effect','effect')):
        definitions.extend([
          ('p07.'+stem+'-args',[port('in','input'),port('out','output','JSON',ref='MCPArgs_'+name)],obj({})),
          ('p07.'+stem+'-text',[port('in','input','JSON',ref='MCPResult_'+name),port('out','output')],obj({}))])
    for tid,ports,cfg in definitions:
        c['nodeDefinitions'].append({'typeId':tid,'version':'0.1.0','executionKind':'builtin','ports':ports+deepcopy(controls),
          'configSchema':cfg,'effect':'none','supportedControls':list(policy())})
    return c

def requirements(nodes):
    rs=[]
    for name in ('echo_text','simulated_effect'):
        if any(n['typeId']=='tool.mcp.'+name for n in nodes):
            rs.append({'slot':'tool.'+name,'kind':'service','required':True,
              'adapter':{'id':'fixture.p04.'+name,'version':'0.1.0','capabilityId':'cap.fixture.p04.'+name},
              'permissions':['synthetic:tool:'+name]})
    return rs

def make_node(tid,id):
    n=node(id,tid,deepcopy(DEFAULTS.get(tid,{})))
    if tid.startswith('tool.mcp.'):
        name=tid[9:];n.update(adapter={'id':'fixture.p04.'+name,'version':'0.1.0','capabilityId':'cap.fixture.p04.'+name},serviceSlot='tool.'+name)
    return n

def sample(effect=False):
    tids=['synth.source','synth.step','p07.model','p07.effect-args' if effect else 'p07.echo-args',
          'tool.mcp.simulated_effect' if effect else 'tool.mcp.echo_text','p07.effect-text' if effect else 'p07.echo-text','synth.output']
    ids=['text','process','model','arguments','tool','extract','output']
    nodes=[make_node(t,i) for t,i in zip(tids,ids)]
    links=[edge(ids[i],ids[i+1],inp='args' if i==3 else 'in',index=i) for i in range(6)]
    w={'kind':'workflow','schemaVersion':'0.1.0-draft.1','workflowId':'p07-workbench','version':{'revision':'draft-1'},
       'title':'合成文本 · MCP 验证','catalogLock':{'resourceRef':'catalog:core','sha256':hashlib.sha256(CATALOG.read_bytes()).hexdigest()},
       'inputSchema':obj({}),'outputSchema':{'type':'string'},'environmentRequirements':requirements(nodes),
       'graph':{'nodes':nodes,'edges':links},'subgraphs':{},'executionPolicy':policy(),'extensions':{'aos:fixture-only':True}}
    positions={id:{'x':(i%4)*270,'y':(i//4)*240} for i,id in enumerate(ids)}
    return {'workflow':w,'layout':{'version':'aos-layout/0.1','positions':positions}}

def environment():
    e=mcp_environment('echo_text'); e['profileId']='p07-windows-x64'
    e['services']={}
    for name in ('echo_text','simulated_effect'):
        s=mcp_environment(name)['services']['tool.query'];e['services']['tool.'+name]=s
    e['extensions']['aos:allowed-tools']=['echo_text','simulated_effect']
    e['extensions']['aos:programs']['program:aos-p04-server']['p006:wrapperSha256']=hashlib.sha256((HERE/'mcp_server_entry.py').read_bytes()).hexdigest()
    return e

def request(w):
    return {'kind':'run-request','schemaVersion':w['schemaVersion'],'workflowId':w['workflowId'],
            'workflowRevision':w['version']['revision'],'environmentProfile':'p07-windows-x64','inputs':{}}

if __name__=='__main__':
    CATALOG.parent.mkdir(exist_ok=True);write(CATALOG,build_catalog())
    write(HERE/'fixtures/default.document.json',sample());write(HERE/'fixtures/approval.document.json',sample(True))
