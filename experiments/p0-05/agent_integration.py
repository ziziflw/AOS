"""D3 produces external facts; C1 subclass alone commits local workflow state."""
import asyncio,hashlib,json,time,uuid
import httpx
from copy import deepcopy
from pathlib import Path
from urllib.parse import urlsplit
from jsonschema import Draft202012Validator
from bootstrap_agent import HERE,ROOT,read,write,digest,ContractError,OutcomeError
from agent_cases import FIX,workflow,binding,artifact_digest
from agent_specs import RESULT
from agent_client import AgentClient
from runtime import Runtime
from contracts import Contracts
from store import StateStore
from mocks import MockRegistry,SyntheticSystem,Result
from common import pointer

def query_error(exc):
    cause=exc
    while getattr(cause,'__cause__',None) is not None:cause=cause.__cause__
    if isinstance(cause,(json.JSONDecodeError,ValueError)):return 'AGENT_PROTOCOL_ERROR'
    if isinstance(cause,httpx.RequestError):return 'AGENT_CONNECTION_LOST'
    return 'AGENT_REMOTE_QUERY_ERROR'

def identity(runtime,key):
    state=runtime.snapshot;n=state['nodes'][key];spec=runtime.spec(key);a=n['attempts'][-1]
    return {'runId':state['runId'],'nodeKey':key,'nodeTypeVersion':spec['typeVersion'],'attemptId':a['id'],'attemptNumber':a['number'],
            'operationId':n['operationId'],'workflowRevision':state['workflowRevision'],'skill':spec['config']['skill']}

class AgentRuntime(Runtime):
    def _validate_environment(self):
        e=self.environment;self.c.v.validate(e)
        if e['platform']!={'os':'windows','arch':'x64'}:raise ContractError('TARGET_NOT_VERIFIED')
        if e['profileId']!=self.c.request['environmentProfile']:raise ContractError('ENVIRONMENT_PROFILE_MISMATCH')
        if e['extensions'].get('aos:agent-artifact')!=artifact_digest():raise ContractError('AGENT_ARTIFACT_DRIFT')
        launch=e['extensions']['aos:programs']['program:aos-p05-agent']
        if Path(launch['executable']).resolve()!=(HERE/'.venv/Scripts/python.exe').resolve() or not Path(launch['executable']).is_file():raise ContractError('AGENT_PROGRAM_MISSING')
        if launch['args']!=['-B','-X','utf8',str(HERE/'agent_service.py')]:raise ContractError('AGENT_COMMAND_DENIED')
        for r in self.c.w['environmentRequirements']:
            b=e['services'].get(r['slot']);remote=e['extensions']['aos:agent-services'].get(r['slot'])
            if not b or not remote or b['adapter']!=r['adapter']:raise ContractError('AGENT_BINDING_MISSING')
            expected=['synthetic:agent:'+remote['agent']+':'+remote['skill']]
            if r['permissions']!=expected:raise ContractError('AGENT_PERMISSION_DENIED')
            if b['target']!=self.c.adapters[(b['adapter']['id'],b['adapter']['version'])]['capability']['selector']:raise ContractError('AGENT_TARGET_DRIFT')
            u=urlsplit(remote['endpoint'])
            if u.scheme!='http' or u.hostname!='127.0.0.1' or not u.port or u.path:raise ContractError('NONLOCAL_AGENT_DENIED')
            if remote['binding']!='JSONRPC' or remote['protocolVersion']!='1.0':raise ContractError('AGENT_PROTOCOL_UNSUPPORTED')
            if e['connections'].get(b['connectionRef'])!={'transport':'cli','programRef':'program:aos-p05-agent','environmentRefs':[]}:raise ContractError('AGENT_CONNECTION_DENIED')
    def _recover_inflight(self,key):
        n=self._state['nodes'][key];ext=n.get('external');spec=self.spec(key)
        allowed=ext and (ext.get('taskId') or self.environment['extensions'].get('aos:correlation-reconcile'))
        if spec['typeId'].startswith('agent.synthetic') and allowed and not self._state['cancelRequested'] and n['state']=='running':
            if ext['identity']!=identity(self,key):raise ContractError('RECOVERY_AGENT_IDENTITY_MISMATCH')
            self._change('agent-query-recovery-planned',lambda s:s['nodes'][key].update(phase='agent-query-resume'),key=key,taskId=ext.get('taskId'))
        else:super()._recover_inflight(key)
    async def drive(self):
        for key,n in list(self._state['nodes'].items()):
            if n['state']=='running' and n['phase']=='agent-query-resume' and key not in self._tasks:
                self._change('agent-query-resumed',lambda s,key=key:s['nodes'][key].update(phase='waiting-agent-query'),key=key)
                self._cancels[key]=asyncio.Event();a=n['attempts'][-1]
                self._tasks[key]=asyncio.create_task(self._execute(key,deepcopy(a['inputs']),a['id']))
        return await super().drive()
    def intent(self,key,local,remote,card_digest):
        n=self._state['nodes'][key]
        if n.get('external'):return
        ext={'identity':deepcopy(local),'messageId':'msg-'+n['operationId'],'contextId':'ctx-'+local['runId'],'taskId':None,
             'deadlineEpoch':n['startedAt']+self.spec(key)['config']['waitTimeoutMs']/1000,
             'endpoint':remote['endpoint'],'agent':remote['agent'],'cardDigest':card_digest,'stage':'submit-intent','lastSequence':-1,'remoteState':None}
        self._change('agent-submit-intent',lambda s:s['nodes'][key].update(external=ext,phase='agent-submitting'),key=key,operationId=n['operationId'])
    def observation(self,key,task):
        n=self._state['nodes'][key];ext=n['external'];md=task.get('metadata',{});expected=identity(self,key)
        if n['state'] not in ('running','cancel-requested'):
            self._event('late-agent-observation-discarded',key=key,taskId=task.get('id'));return False
        if md.get('aos:identity')!=expected or md.get('aos:agent')!=ext['agent'] or task.get('contextId')!=ext['contextId']:
            raise OutcomeError('AGENT_IDENTITY_MISMATCH',side_effect='unknown')
        if ext['taskId'] is not None and task.get('id')!=ext['taskId']:raise OutcomeError('AGENT_TASK_ID_MISMATCH',side_effect='unknown')
        try:uuid.UUID(task['id'])
        except (KeyError,ValueError,TypeError):raise OutcomeError('AGENT_TASK_ID_INVALID',side_effect='unknown') from None
        if md.get('aos:messageId')!=ext['messageId'] or not task.get('id'):raise OutcomeError('AGENT_IDENTITY_MISMATCH',side_effect='unknown')
        seq=md.get('aos:sequence');progress=md.get('aos:progress');state=task.get('status',{}).get('state')
        states={'TASK_STATE_SUBMITTED','TASK_STATE_WORKING','TASK_STATE_COMPLETED','TASK_STATE_FAILED','TASK_STATE_CANCELED','TASK_STATE_REJECTED','TASK_STATE_INPUT_REQUIRED','TASK_STATE_AUTH_REQUIRED'}
        if type(seq) not in (int,float) or int(seq)!=seq or type(progress) not in (int,float) or not 0<=progress<=100 or state not in states:raise OutcomeError('AGENT_STATUS_INVALID',side_effect='unknown')
        if seq<ext['lastSequence']:raise OutcomeError('AGENT_STATE_REGRESSION',side_effect='unknown')
        terminal={'TASK_STATE_COMPLETED','TASK_STATE_FAILED','TASK_STATE_CANCELED','TASK_STATE_REJECTED'}
        if ext['remoteState'] in terminal and state!=ext['remoteState']:raise OutcomeError('AGENT_TERMINAL_REGRESSION',side_effect='unknown')
        if seq==ext['lastSequence'] and ext['remoteState']!=state:raise OutcomeError('AGENT_SEQUENCE_CONFLICT',side_effect='unknown')
        phases={'TASK_STATE_INPUT_REQUIRED':'waiting-agent-input','TASK_STATE_AUTH_REQUIRED':'waiting-agent-auth','TASK_STATE_COMPLETED':'waiting-agent-artifact'}
        phase=phases.get(state,'waiting-agent-query')
        def save(s):
            e=s['nodes'][key]['external'];e.update(taskId=task['id'],stage='accepted',lastSequence=seq,remoteState=state,progress=progress,lastTask=deepcopy(task))
            if s['nodes'][key]['state']=='running':s['nodes'][key]['phase']=phase
        kind='agent-observation-duplicate' if seq==ext['lastSequence'] else 'agent-observed'
        self._change(kind,save,key=key,taskId=task['id'],remoteState=state,progress=progress,remoteSequence=seq)
        return True
    def waiting(self,key,phase,code):
        self._change('agent-waiting',lambda s:s['nodes'][key].update(phase=phase),key=key,phase=phase,code=code)
    def _terminal(self,key,state,**kw):
        n=self._state['nodes'][key];spec=self.spec(key)
        if spec['typeId'].startswith('agent.synthetic'):
            ext=n.get('external',{});err=kw.get('error') or {}
            if err.get('code')=='AGENT_CANCEL_CONFIRMED':
                if ext.get('remoteState')!='TASK_STATE_CANCELED' or ext.get('identity')!=identity(self,key):raise ContractError('UNVERIFIED_CANCEL_RECEIPT')
                state='cancelled'
            if state=='succeeded' and n.get('approvalId'):
                a=self._state['approvals'][n['approvalId']]
                if a['status']!='consumed' or a['expiresAt']<=time.time():
                    state='unknown';kw={'error':{'code':'AGENT_AUTH_RESULT_STALE','message':'Authorization no longer permits publication','category':'permission','retryable':False,'sideEffect':'unknown'}}
        return super()._terminal(key,state,**kw)

class AgentRegistry(MockRegistry):
    def __init__(self,system,directory,env):
        super().__init__(system);self.dir=Path(directory);self.env=deepcopy(env);self.runtime=None;self.clients=[]
    def metadata(self,tid):
        if tid in ('p05.input','p05.join','synth.output-agent','synth.output-agents'):return {'effect':'none'}
        if tid=='agent.synthetic':return {'effect':'read'}
        if tid=='agent.synthetic.effect':return {'effect':'write'}
        return super().metadata(tid)
    def authorized(self,ctx):
        s=self.runtime.snapshot;n=s['nodes'][ctx.key]
        if s['cancelRequested'] or ctx.cancel.is_set():raise OutcomeError('AGENT_LOCAL_CANCELLED',side_effect='unknown')
        if n['state']!='running' or n['attempts'][-1]['id']!=ctx.attempt_id or n['operationId']!=ctx.operation_id:raise ContractError('AGENT_DISPATCH_MISMATCH')
        if n.get('approvalId'):
            a=s['approvals'][n['approvalId']]
            if a['status']!='consumed' or a['expiresAt']<=time.time() or a['fingerprint']!=self.runtime._fingerprint(ctx.key,ctx.inputs):raise OutcomeError('AGENT_AUTH_RESULT_STALE',side_effect='unknown')
        elif ctx.node['typeId']=='agent.synthetic.effect':raise ContractError('AGENT_APPROVAL_REQUIRED')
    async def reconcile(self,client,key,ext):
        candidates=await client.lookup(ext['contextId'])
        matches=[t for t in candidates if t.get('metadata',{}).get('aos:identity')==ext['identity'] and t.get('metadata',{}).get('aos:messageId')==ext['messageId']]
        if len(matches)!=1:raise OutcomeError('AGENT_SUBMISSION_UNVERIFIABLE',side_effect='unknown')
        self.runtime._event('agent-submission-reconciled',key=key,taskId=matches[0]['id']);return matches[0]
    async def invoke(self,ctx):
        tid=ctx.node['typeId']
        if tid=='p05.input':return Result({'out':deepcopy(pointer(ctx.scope_inputs,ctx.node['config']['inputPath']))})
        if tid=='p05.join':return Result({'out':deepcopy(ctx.inputs['items'])})
        if not tid.startswith('agent.synthetic'):return await super().invoke(ctx)
        if self.runtime is None:raise ContractError('TRUSTED_CONTROLLER_REQUIRED')
        self.authorized(ctx);remote=self.env['extensions']['aos:agent-services'][ctx.node['serviceSlot']]
        client=AgentClient(self.dir/('agent-client-'+str(len(self.clients)+1)),remote['endpoint'],remote['agent']);self.clients.append(client)
        existing=self.runtime.snapshot['nodes'][ctx.key].get('external');submitted=bool(existing)
        started=self.runtime.snapshot['nodes'][ctx.key]['startedAt']
        deadline_epoch=existing['deadlineEpoch'] if existing else started+ctx.node['config']['waitTimeoutMs']/1000
        deadline=time.monotonic()+max(0,deadline_epoch-time.time())
        if time.time()>=deadline_epoch:raise OutcomeError('AGENT_WAIT_TIMEOUT',side_effect='unknown')
        try:
            await client.open();self.authorized(ctx)
            local=identity(self.runtime,ctx.key)
            if not existing:
                self.runtime.intent(ctx.key,local,remote,client.card_digest);submitted=True
                ext=self.runtime.snapshot['nodes'][ctx.key]['external']
                try:task=await client.send(ctx.inputs['in'],local,ext['messageId'],ext['contextId'])
                except Exception:
                    self.runtime.waiting(ctx.key,'agent-submit-unknown','AGENT_SUBMIT_RESPONSE_LOST')
                    if not self.env['extensions']['aos:correlation-reconcile']:raise OutcomeError('AGENT_SUBMIT_UNKNOWN',side_effect='unknown') from None
                    task=await self.reconcile(client,ctx.key,ext)
                self.runtime.observation(ctx.key,task)
            else:
                if existing['identity']!=local or existing['endpoint']!=remote['endpoint'] or existing['cardDigest']!=client.card_digest:raise OutcomeError('AGENT_RESUME_BINDING_MISMATCH',side_effect='unknown')
                task=await client.query(existing['taskId']) if existing['taskId'] else await self.reconcile(client,ctx.key,existing)
                self.runtime.observation(ctx.key,task)
            errors=0;last_error='AGENT_WAIT_TIMEOUT'
            while time.monotonic()<deadline:
                ext=self.runtime.snapshot['nodes'][ctx.key]['external'];state=ext['remoteState'];task=ext['lastTask'];task_id=ext['taskId']
                if ctx.cancel.is_set() or self.runtime.snapshot['cancelRequested']:
                    self.runtime._event('agent-cancel-requested',key=ctx.key,taskId=task_id)
                    try:
                        canceled=await client.cancel(task_id);self.runtime.observation(ctx.key,canceled)
                        if canceled['status']['state']=='TASK_STATE_CANCELED':raise OutcomeError('AGENT_CANCEL_CONFIRMED',side_effect='confirmed')
                    except OutcomeError:raise
                    except Exception:pass
                    try:self.runtime.observation(ctx.key,await client.query(task_id))
                    except Exception:pass
                    raise OutcomeError('AGENT_CANCEL_UNCONFIRMED',side_effect='unknown')
                if state=='TASK_STATE_CANCELED':raise OutcomeError('AGENT_CANCEL_CONFIRMED',side_effect='confirmed')
                if state=='TASK_STATE_REJECTED':raise OutcomeError('AGENT_REJECTED',side_effect='not-started')
                if state=='TASK_STATE_FAILED':raise OutcomeError('AGENT_FAILED',side_effect='confirmed')
                if state=='TASK_STATE_COMPLETED' and task.get('artifacts'):
                    self.authorized(ctx)
                    output=await self.validate_artifact(client,ctx,task);return Result({'out':output})
                if state=='TASK_STATE_COMPLETED':last_error='AGENT_RESULT_UNAVAILABLE'
                await asyncio.sleep(ctx.node['config']['pollMs']/1000)
                try:
                    task=await client.query(task_id);self.runtime.observation(ctx.key,task);errors=0
                except OutcomeError:raise
                except Exception as exc:
                    errors+=1;last_error=query_error(exc)
                    self.runtime.waiting(ctx.key,'waiting-agent-reconnect',last_error)
                    if errors>=4:raise OutcomeError(last_error,side_effect='unknown') from None
            raise OutcomeError(last_error,side_effect='unknown')
        except OutcomeError:raise
        except asyncio.CancelledError:raise OutcomeError('AGENT_CLIENT_INTERRUPTED',side_effect='unknown')
        except ContractError as exc:
            if submitted:raise OutcomeError(exc.code,side_effect='unknown') from None
            raise
        except Exception:raise OutcomeError('AGENT_PROTOCOL_ERROR' if submitted else 'AGENT_DISCOVERY_UNAVAILABLE',side_effect='unknown' if submitted else 'not-started') from None
        finally:await client.close()
    async def validate_artifact(self,client,ctx,task):
        try:
            if len(task['artifacts'])!=1:raise ValueError()
            artifact=task['artifacts'][0];parts=artifact['parts']
            if artifact['artifactId']!='result-'+task['id'] or len(parts)!=2:raise ValueError()
            output=parts[0]['data']['result'];Draft202012Validator(RESULT).validate(output)
            if (output['taskId'],output['operationId'],output['agent'])!=(task['id'],ctx.operation_id,client.name):raise ValueError()
            ref=output['artifact'];expected='artifact:'+client.name+'/'+task['id']+'/result.json'
            if ref['resourceUri']!=expected or ref['mediaType']!='application/json':raise ValueError()
            content=await client.artifact(task['id'],parts[1]['url'])
            if len(content)!=ref['sizeBytes'] or hashlib.sha256(content).hexdigest()!=ref['sha256']:raise ValueError()
            parsed=json.loads(content)
            if parsed!={k:output[k] for k in ('text','agent','taskId','operationId')}:raise ValueError()
            target=self.dir/'artifacts'/ref['sha256'];target.parent.mkdir(exist_ok=True);target.write_bytes(content)
            self.system.db.execute('INSERT OR REPLACE INTO artifacts VALUES(?,?,?)',(expected,content,'application/json'))
            self.runtime._event('agent-artifact-validated',key=ctx.key,taskId=task['id'],sha256=ref['sha256'],resourceUri=expected)
            return output
        except Exception:raise OutcomeError('AGENT_ARTIFACT_INVALID',side_effect='confirmed') from None
    async def close(self):
        for c in self.clients:await c.close()

class Session:
    def __init__(self,directory,v,hosts=None,*,parallel=False,skill='echo',mode='normal',delay=400,timeout=3000,reconcile=False,change=None,recover=False,hook=None,ttl=300):
        self.dir=Path(directory);self.dir.mkdir(parents=True,exist_ok=True)
        if not recover:
            w,r=workflow(parallel=parallel,skill=skill,mode=mode,delay=delay,timeout=timeout);e=binding(hosts,skill,reconcile=reconcile)
            if change:change(w,r,e)
            write(self.dir/'workflow.json',w);write(self.dir/'request.json',r);write(self.dir/'environment.json',e)
        w,r,e=(read(self.dir/(n+'.json')) for n in ('workflow','request','environment'))
        self.system=SyntheticSystem(self.dir/'local-artifacts.sqlite');self.registry=AgentRegistry(self.system,self.dir,e);self.store=None
        try:
            for n in w['graph']['nodes']:
                if n['typeId'].startswith('agent.synthetic') and (n['policy']['maxAttempts']!=1 or n['policy']['retryMode']!='never'):raise ContractError('AGENT_RETRY_UNSUPPORTED')
            c=Contracts(w,r,FIX/'catalog.json',v,self.registry);self.store=StateStore(self.dir/'run.sqlite',hook)
            self.runtime=AgentRuntime(c,self.store,self.registry,e,approval_ttl=ttl,cancel_grace=1)
            self.registry.runtime=self.runtime
        except BaseException:
            if self.store:self.store.close()
            self.system.close();raise
    def export(self,label='final'):
        write(self.dir/(label+'-snapshot.json'),self.runtime.snapshot);write(self.dir/(label+'-events.json'),self.store.events())
    async def close(self):
        await self.runtime.close();await self.registry.close();self.export();self.store.close();self.system.close()
