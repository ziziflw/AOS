"""P0-02-format fixtures and local EnvironmentBinding, never shell text in graphs."""
import hashlib,sys
from copy import deepcopy
from bootstrap import HERE,ROOT,read,write
from tool_specs import SPECS,obj,catalog as original,descriptor,signature
from fixtures import policy,port
FIX=HERE/'fixtures'
BASE=ROOT/'research/02-node-contracts/examples'
def build():
    FIX.mkdir(exist_ok=True)
    c=deepcopy(original)
    controls=deepcopy(c['nodeDefinitions'][0]['ports'][-3:])
    original_ad=deepcopy(next(a for a in c['adapterDefinitions'] if a['id']=='fixture.tool.mcp'))
    for name,(ins,outs,effect) in SPECS.items():
        c['types']['MCPArgs_'+name]=ins; c['types']['MCPResult_'+name]=outs
        for tid,ports,kind,cfg in [
            ('p04.input.'+name,[port('out','output','JSON',ref='MCPArgs_'+name)],'builtin',obj({})),
            ('tool.mcp.'+name,[port('args','input','JSON',ref='MCPArgs_'+name),port('out','output','JSON',ref='MCPResult_'+name)],'tool',obj({'operation':{'const':name}})),
            ('synth.output-'+name,[port('in','input','JSON',ref='MCPResult_'+name)],'builtin',obj({}))]:
            c['nodeDefinitions'].append({'typeId':tid,'version':'0.1.0','executionKind':kind,'ports':ports+deepcopy(controls),
                'configSchema':cfg,'effect':effect if kind=='tool' else 'none','supportedControls':list(policy())})
        ad=deepcopy(original_ad); ad.update(id='fixture.p04.'+name,version='0.1.0',effect=effect)
        ad['capability'].update(id='cap.fixture.p04.'+name,selector={'provider':'aos-local','model':name,'apiVersion':'0.1.0','interface':'mcp-stdio'},
            parameterSchema=obj({'operation':{'const':'query' if name=='structured_result' else name}}),retrySafety='never' if effect=='write' else 'safe-read',cancel='best-effort')
        for platform in ad['platforms']:
            platform['protocol']={'name':'MCP','version':'2025-11-25'}
        c['adapterDefinitions'].append(ad)
    write(FIX/'catalog.json',c)
    write(FIX/'tool-lock.json',{name:{'descriptor':descriptor(name),'signature':signature(descriptor(name))} for name in SPECS})
    for name in SPECS:
        if name=='structured_result':
            w=read(BASE/'scenario-b.workflow.json'); r=read(BASE/'scenario-b.run-request.json')
            w['version']={'revision':'scenario-b-p04-r1','parentRevision':'scenario-b-r1'}
            w['extensions']={'aos:fixture-only':True,'aos:protocol-experiment':'p0-04'}
        else:
            w=read(BASE/'scenario-b.workflow.json'); w['workflowId']='p04-'+name
            w['version']={'revision':'p04-'+name+'-r1'}
            w['inputSchema']=obj({'arguments':{'$ref':'#/$defs/MCPArgs_'+name}})
            w['outputSchema']={'$ref':'#/$defs/MCPResult_'+name}
            w['graph']['nodes']=[deepcopy(w['graph']['nodes'][i]) for i in (0,2,4)]
            a,b,d=w['graph']['nodes']; a.update(id='input',typeId='p04.input.'+name,config={})
            b.update(id='tool',typeId='tool.mcp.'+name,config={'operation':name})
            d.update(id='output',typeId='synth.output-'+name)
            w['graph']['edges']=[{'id':'e1','kind':'data','from':{'node':'input','port':'out'},'to':{'node':'tool','port':'args'},'order':0},
                                 {'id':'e2','kind':'data','from':{'node':'tool','port':'out'},'to':{'node':'output','port':'in'},'order':0}]
            defaults={'echo_text':{'text':'合成 echo'},'add_numbers':{'a':2,'b':3},'delayed_result':{'delayMs':100,'value':'synthetic-delay'},
                      'simulated_failure':{'mode':'tool-error'},'simulated_effect':{'value':'synthetic-write'}}
            r={'kind':'run-request','schemaVersion':w['schemaVersion'],'workflowId':w['workflowId'],'workflowRevision':w['version']['revision'],
               'environmentProfile':'p04-windows-x64','inputs':{'arguments':defaults[name]}}
            w['extensions']={'aos:fixture-only':True}
        adref={'id':'fixture.p04.'+name,'version':'0.1.0','capabilityId':'cap.fixture.p04.'+name}
        tool=next(n for n in w['graph']['nodes'] if n['id']=='tool'); tool['adapter']=adref
        tool['policy'].update(maxAttempts=1,retryMode='never')
        w['environmentRequirements']=[{'slot':'tool.query','kind':'service','required':True,'adapter':adref,'permissions':['synthetic:tool:'+name]}]
        if name=='structured_result': w['environmentRequirements'].append({'slot':'workspace:source','kind':'resource','required':True,'permissions':['resource:read']})
        w['catalogLock']['sha256']=hashlib.sha256((FIX/'catalog.json').read_bytes()).hexdigest()
        r['workflowRevision']=w['version']['revision']; r['environmentProfile']='p04-windows-x64'
        write(FIX/(name+'.workflow.json'),w); write(FIX/(name+'.request.json'),r)
        write(FIX/(name+'.environment.json'),environment(name))
    return c
def environment(name,mode='normal'):
    adref={'id':'fixture.p04.'+name,'version':'0.1.0','capabilityId':'cap.fixture.p04.'+name}
    return {'kind':'environment-binding','schemaVersion':'0.1.0-draft.1','profileId':'p04-windows-x64','platform':{'os':'windows','arch':'x64'},
      'services':{'tool.query':{'serviceRef':'service:p04','connectionRef':'connection:p04','credentialRef':'secret:unused','adapter':adref,
        'target':{'provider':'aos-local','model':name,'apiVersion':'0.1.0','interface':'mcp-stdio'}}},
      'resources':{'workspace:source':{'mountPath':'memory:synthetic','mode':'read'}},
      'credentials':{'secret:unused':{'vaultAlias':'synthetic:no-secret-used','status':'configured'}},
      'connections':{'connection:p04':{'transport':'stdio','programRef':'program:aos-p04-server','environmentRefs':[]}},
      'extensions':{'aos:allowed-tools':[name],'aos:server-artifact-sha256':hashlib.sha256((HERE/'synthetic_server.py').read_bytes()).hexdigest(),
        'aos:programs':{'program:aos-p04-server':{'executable':str(HERE/'.venv/Scripts/python.exe'),
          'args':['-B','-X','utf8',str(HERE/'synthetic_server.py')],'mode':mode}}}}
def inputs(name): return read(FIX/(name+'.workflow.json')),read(FIX/(name+'.request.json'))
if __name__=='__main__': build()
