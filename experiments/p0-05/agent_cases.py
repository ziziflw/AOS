"""Same P0-02 workflow language; extended task JSON types, no remote state in graphs."""
import hashlib
from copy import deepcopy
from bootstrap_agent import HERE,ROOT,read,write,digest
from agent_specs import ORIGINAL,ARGS,RESULT,RESULTS,CONFIG,obj
from fixtures import policy,port
FIX=HERE/'fixtures'
def artifact_digest():return digest({n:hashlib.sha256((HERE/n).read_bytes()).hexdigest() for n in ('agent_service.py','agent_specs.py','bootstrap_agent.py')})
def build():
    FIX.mkdir(exist_ok=True);c=deepcopy(ORIGINAL);c['types'].update(AgentTaskArgs=ARGS,AgentTaskResult=RESULT,AgentTaskResults=RESULTS)
    controls=deepcopy(c['nodeDefinitions'][0]['ports'][-3:])
    specs=[('p05.input',[],[port('out','output','JSON',ref='AgentTaskArgs')],'builtin',obj({'inputPath':{'type':'string'}}),'none'),
      ('agent.synthetic',[port('in','input','JSON',ref='AgentTaskArgs')],[port('out','output','JSON',ref='AgentTaskResult')],'agent',CONFIG,'read'),
      ('agent.synthetic.effect',[port('in','input','JSON',ref='AgentTaskArgs')],[port('out','output','JSON',ref='AgentTaskResult')],'agent',CONFIG,'write'),
      ('p05.join',[port('items','input','JSON',ref='AgentTaskResult',many=True)],[port('out','output','JSON',ref='AgentTaskResults')],'builtin',obj({}),'none'),
      ('synth.output-agent',[port('in','input','JSON',ref='AgentTaskResult')],[],'builtin',obj({}),'none'),
      ('synth.output-agents',[port('in','input','JSON',ref='AgentTaskResults')],[],'builtin',obj({}),'none')]
    for tid,ins,outs,kind,cfg,effect in specs:c['nodeDefinitions'].append({'typeId':tid,'version':'0.1.0','executionKind':kind,'ports':ins+outs+deepcopy(controls),'configSchema':cfg,'effect':effect,'supportedControls':list(policy())})
    original=next(a for a in c['adapterDefinitions'] if a['kind']=='agent')
    for name in ('agentA','agentB'):
        for skill in ('echo','effect'):
            a=deepcopy(original);a.update(id='fixture.p05.'+name+'.'+skill,version='0.1.0',effect='write' if skill=='effect' else 'read')
            a['capability'].update(id='cap.fixture.p05.'+name+'.'+skill,selector={'provider':'aos-local','model':name,'apiVersion':'0.1.0','interface':'a2a-jsonrpc-1.0'},parameterSchema=CONFIG,retrySafety='never',cancel='best-effort')
            for platform in a['platforms']:platform['protocol']={'name':'A2A','version':'1.0'}
            c['adapterDefinitions'].append(a)
    write(FIX/'catalog.json',c)
    for parallel in (False,True):
        label='parallel' if parallel else 'single';w,r=workflow(parallel=parallel);write(FIX/(label+'.workflow.json'),w);write(FIX/(label+'.request.json'),r)
    return c
def args(text='synthetic',mode='normal',delay=400):return {'text':text,'delayMs':delay,'mode':mode}
def adapter(name,skill):return {'id':'fixture.p05.'+name+'.'+skill,'version':'0.1.0','capabilityId':'cap.fixture.p05.'+name+'.'+skill}
def node(id,tid,cfg=None):
    p=policy();p['timeoutMs']=10000
    return {'id':id,'typeId':tid,'typeVersion':'0.1.0','enabled':True,'config':cfg or {},'policy':p}
def edge(id,src,dst,inp='in',order=0):return {'id':id,'kind':'data','from':{'node':src,'port':'out'},'to':{'node':dst,'port':inp},'order':order}
def workflow(*,parallel=False,skill='echo',mode='normal',delay=400,timeout=3000):
    names=['agentA','agentB'] if parallel else ['agentA'];nodes=[];edges=[];reqs=[]
    for i,name in enumerate(names):
        source='input'+str(i) if parallel else 'input';target='agent'+str(i) if parallel else 'agent'
        nodes.append(node(source,'p05.input',{'inputPath':'/'+name if parallel else '/arguments'}))
        n=node(target,'agent.synthetic.effect' if skill=='effect' else 'agent.synthetic',{'skill':skill,'pollMs':30,'waitTimeoutMs':timeout})
        n.update(adapter=adapter(name,skill),serviceSlot='agent.'+name);nodes.append(n);edges.append(edge('in'+str(i),source,target))
        if parallel:edges.append(edge('join'+str(i),target,'join',inp='items',order=i))
        else:edges.append(edge('out',target,'output'))
        reqs.append({'slot':'agent.'+name,'kind':'service','required':True,'adapter':adapter(name,skill),'permissions':['synthetic:agent:'+name+':'+skill]})
    if parallel:nodes.append(node('join','p05.join'));edges.append(edge('out','join','output'))
    nodes.append(node('output','synth.output-agents' if parallel else 'synth.output-agent'))
    ident='p05-parallel' if parallel else 'p05-task'
    w={'kind':'workflow','schemaVersion':'0.1.0-draft.1','workflowId':ident,'version':{'revision':ident+'-r1'},'title':'Independent synthetic Agent task',
       'catalogLock':{'resourceRef':'catalog:core','sha256':hashlib.sha256((FIX/'catalog.json').read_bytes()).hexdigest()},
       'inputSchema':obj({name:{'$ref':'#/$defs/AgentTaskArgs'} for name in names} if parallel else {'arguments':{'$ref':'#/$defs/AgentTaskArgs'}}),
       'outputSchema':{'$ref':'#/$defs/AgentTaskResults' if parallel else '#/$defs/AgentTaskResult'},'environmentRequirements':reqs,
       'graph':{'nodes':nodes,'edges':edges},'subgraphs':{},'executionPolicy':policy(),'extensions':{'aos:fixture-only':True}}
    r={'kind':'run-request','schemaVersion':w['schemaVersion'],'workflowId':ident,'workflowRevision':w['version']['revision'],'environmentProfile':'p05-windows-x64',
       'inputs':{n:args(n,mode,delay) for n in names} if parallel else {'arguments':args('synthetic',mode,delay)}}
    return w,r
def binding(hosts,skill='echo',*,reconcile=False):
    e={'kind':'environment-binding','schemaVersion':'0.1.0-draft.1','profileId':'p05-windows-x64','platform':{'os':'windows','arch':'x64'},'services':{},'resources':{},
       'credentials':{'secret:p05':{'vaultAlias':'synthetic:a2a-local','status':'configured'}},'connections':{},
       'extensions':{'aos:agent-services':{},'aos:correlation-reconcile':reconcile,'aos:agent-artifact':artifact_digest(),'aos:programs':
          {'program:aos-p05-agent':{'executable':str(HERE/'.venv/Scripts/python.exe'),'args':['-B','-X','utf8',str(HERE/'agent_service.py')]}}}}
    for name,host in hosts.items():
        a=adapter(name,skill);slot='agent.'+name
        e['services'][slot]={'serviceRef':'service:'+name,'connectionRef':'connection:'+name,'credentialRef':'secret:p05','adapter':a,
            'target':{'provider':'aos-local','model':name,'apiVersion':'0.1.0','interface':'a2a-jsonrpc-1.0'}}
        e['connections']['connection:'+name]={'transport':'cli','programRef':'program:aos-p05-agent','environmentRefs':[]}
        e['extensions']['aos:agent-services'][slot]={'endpoint':host.endpoint,'agent':name,'binding':'JSONRPC','protocolVersion':'1.0','skill':skill}
    return e
if __name__=='__main__':build()
