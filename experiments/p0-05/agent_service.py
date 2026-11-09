"""Independent A2A SDK service. It owns task state, never imports workflow runtime."""
import asyncio,argparse,hashlib,json,os,socket,sqlite3,time,uuid
from datetime import datetime,timezone
from pathlib import Path
from contextlib import asynccontextmanager
from bootstrap_agent import HERE,SECRET,read,write,dumps,digest,jsonl
from agent_specs import ARGS,card
from jsonschema import Draft202012Validator
from google.protobuf.json_format import ParseDict,MessageToDict
from a2a.types import a2a_pb2 as p
from a2a.server.request_handlers.request_handler import RequestHandler,validate_request_params
from a2a.server.routes import create_jsonrpc_routes,create_agent_card_routes
from a2a.utils.errors import InvalidParamsError,TaskNotFoundError,TaskNotCancelableError,UnsupportedOperationError,InternalError
from starlette.applications import Starlette
from starlette.responses import Response
from starlette.routing import Route
import uvicorn
TERMINAL={'TASK_STATE_COMPLETED','TASK_STATE_FAILED','TASK_STATE_CANCELED','TASK_STATE_REJECTED'}
def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')

class Tasks(RequestHandler):
    def __init__(self,directory,name,base):
        self.dir=directory;self.name=name;self.base=base;self.workers={};self.query_counts={}
        self.db=sqlite3.connect(directory/'agent.sqlite',isolation_level=None)
        self.db.execute('PRAGMA journal_mode=WAL');self.db.execute('PRAGMA synchronous=FULL')
        self.db.executescript('''CREATE TABLE IF NOT EXISTS tasks(id TEXT PRIMARY KEY,messageId TEXT UNIQUE,contextId TEXT,requestDigest TEXT,body TEXT,args TEXT,identity TEXT);
        CREATE TABLE IF NOT EXISTS events(seq INTEGER PRIMARY KEY,kind TEXT,body TEXT);
        CREATE TABLE IF NOT EXISTS artifacts(taskId TEXT PRIMARY KEY,content BLOB);
        CREATE TABLE IF NOT EXISTS effects(operationId TEXT PRIMARY KEY,taskId TEXT);
        ''')
    def event(self,kind,**body):
        self.db.execute('INSERT INTO events(kind,body) VALUES(?,?)',(kind,json.dumps({'time':time.time(),'pid':os.getpid(),**body},ensure_ascii=False)))
    def task(self,tid):
        row=self.db.execute('SELECT body FROM tasks WHERE id=?',(tid,)).fetchone()
        if not row: raise TaskNotFoundError()
        return json.loads(row[0])
    def save(self,t): self.db.execute('UPDATE tasks SET body=? WHERE id=?',(dumps(t),t['id']))
    def advance(self,tid,state,progress,artifacts=None):
        t=self.task(tid)
        if t['status']['state'] in TERMINAL: return t
        t['status']={'state':state,'timestamp':now()}
        t['metadata']['aos:sequence']+=1;t['metadata']['aos:progress']=progress
        if artifacts is not None: t['artifacts']=artifacts
        self.save(t);self.event('task-state',taskId=tid,state=state,progress=progress,sequence=t['metadata']['aos:sequence']);return t
    @validate_request_params
    async def on_message_send(self,params,context):
        data=MessageToDict(params);msg=data['message'];md=msg.get('metadata',{});identity=md.get('aos:identity')
        if not identity or len(msg.get('parts',[]))!=1 or 'data' not in msg['parts'][0]: raise InvalidParamsError('Typed task and identity required')
        args=msg['parts'][0]['data']
        try: Draft202012Validator(ARGS).validate(args)
        except Exception: raise InvalidParamsError('Invalid synthetic task parameters') from None
        if not params.configuration.return_immediately: raise InvalidParamsError('This profile requires returnImmediately=true')
        request_digest=digest([args,identity]);message_id=msg['messageId']
        existing=self.db.execute('SELECT id,requestDigest FROM tasks WHERE messageId=?',(message_id,)).fetchone()
        if existing:
            if existing[1]!=request_digest: raise InvalidParamsError('Message identity reused with different content')
            self.event('submit-deduplicated',taskId=existing[0],messageId=message_id)
            return ParseDict(self.task(existing[0]),p.Task())
        tid=str(uuid.uuid4());t={'id':tid,'contextId':msg['contextId'],'status':{'state':'TASK_STATE_SUBMITTED','timestamp':now()},
            'metadata':{'aos:identity':identity,'aos:messageId':message_id,'aos:sequence':1,'aos:progress':0,'aos:agent':self.name}}
        self.db.execute('BEGIN IMMEDIATE')
        try:
            self.db.execute('INSERT INTO tasks VALUES(?,?,?,?,?,?,?)',(tid,message_id,msg['contextId'],request_digest,dumps(t),dumps(args),dumps(identity)))
            self.event('task-created',taskId=tid,messageId=message_id,contextId=msg['contextId'],identity=identity,args=args)
            self.db.execute('COMMIT')
        except BaseException:
            self.db.execute('ROLLBACK');raise
        if args['mode']=='reject': t=self.advance(tid,'TASK_STATE_REJECTED',0)
        else: self.workers[tid]=asyncio.create_task(self.work(tid))
        return ParseDict(t,p.Task())
    async def work(self,tid):
        row=self.db.execute('SELECT args,identity FROM tasks WHERE id=?',(tid,)).fetchone();args,identity=map(json.loads,row)
        mode=args['mode']
        try:
            if self.task(tid)['status']['state']=='TASK_STATE_SUBMITTED': self.advance(tid,'TASK_STATE_WORKING',10)
            if mode in ('wait-input','wait-auth'):
                self.advance(tid,'TASK_STATE_INPUT_REQUIRED' if mode=='wait-input' else 'TASK_STATE_AUTH_REQUIRED',10);return
            await asyncio.sleep(args['delayMs']/2000)
            if self.task(tid)['status']['state'] in TERMINAL:return
            self.advance(tid,'TASK_STATE_WORKING',60)
            await asyncio.sleep(args['delayMs']/2000)
            if self.task(tid)['status']['state'] in TERMINAL:return
            if mode=='fail':self.advance(tid,'TASK_STATE_FAILED',60);return
            data={'text':args['text'].upper(),'agent':self.name,'taskId':tid,'operationId':identity['operationId']}
            content=dumps(data).encode('utf-8');sha=hashlib.sha256(content).hexdigest()
            ref={'resourceUri':'artifact:'+self.name+'/'+tid+'/result.json','mediaType':'application/json','sizeBytes':len(content),'sha256':sha}
            result={**data,'artifact':ref}
            if mode=='bad-result':result['text']=123
            if mode=='bad-reference':result['artifact']['resourceUri']='C:/Users/Administrator/private.txt'
            arts=[{'artifactId':'result-'+tid,'name':'synthetic-result','parts':[{'data':{'result':result}},
                {'url':self.base+'/artifacts/'+tid,'filename':'result.json','mediaType':'application/json'}]}]
            self.db.execute('BEGIN IMMEDIATE')
            try:
                self.db.execute('INSERT OR REPLACE INTO artifacts VALUES(?,?)',(tid,content))
                if identity.get('skill')=='effect':self.db.execute('INSERT OR IGNORE INTO effects VALUES(?,?)',(identity['operationId'],tid))
                self.advance(tid,'TASK_STATE_COMPLETED',100,arts);self.db.execute('COMMIT')
            except BaseException:self.db.execute('ROLLBACK');raise
        except asyncio.CancelledError:
            self.event('worker-stopped',taskId=tid);raise
    @validate_request_params
    async def on_get_task(self,params,context):
        t=self.task(params.id);row=self.db.execute('SELECT args FROM tasks WHERE id=?',(params.id,)).fetchone();mode=json.loads(row[0])['mode']
        self.event('get-task',taskId=params.id)
        count=self.query_counts.get(params.id,0)+1;self.query_counts[params.id]=count
        if mode=='service-exit':os._exit(81)
        if mode in ('query-unavailable','bad-secret-error'): raise InternalError('Synthetic failure '+(SECRET if mode=='bad-secret-error' else 'unavailable'))
        if mode=='wrong-identity': t['metadata']['aos:identity']['operationId']='wrong-operation'
        if mode=='wrong-task': t['id']='wrong-task-id'
        if mode=='stale-state' and count>=2:
            t['metadata']['aos:sequence']=0;t['status']['state']='TASK_STATE_SUBMITTED'
        if mode in ('result-delayed','result-never') and t['status']['state']=='TASK_STATE_COMPLETED' and (mode=='result-never' or count<20):t.pop('artifacts',None)
        return ParseDict(t,p.Task())
    @validate_request_params
    async def on_list_tasks(self,params,context):
        self.event('list-tasks',contextId=params.context_id)
        rows=self.db.execute('SELECT body FROM tasks WHERE contextId=? ORDER BY id',(params.context_id,)).fetchall()
        return p.ListTasksResponse(tasks=[ParseDict(json.loads(x[0]),p.Task()) for x in rows],page_size=len(rows),total_size=len(rows),next_page_token='')
    @validate_request_params
    async def on_cancel_task(self,params,context):
        t=self.task(params.id);mode=json.loads(self.db.execute('SELECT args FROM tasks WHERE id=?',(params.id,)).fetchone()[0])['mode']
        self.event('cancel-received',taskId=params.id)
        if t['status']['state']=='TASK_STATE_CANCELED':return ParseDict(t,p.Task())
        if mode=='cancel-unsupported':raise UnsupportedOperationError('Cancellation not supported for this synthetic task')
        if mode=='finish-after-cancel' or t['status']['state'] in TERMINAL:raise TaskNotCancelableError('Task cannot be canceled')
        t=self.advance(params.id,'TASK_STATE_CANCELED',t['metadata']['aos:progress'])
        if params.id in self.workers:self.workers[params.id].cancel()
        self.event('cancel-confirmed',taskId=params.id);return ParseDict(t,p.Task())
    async def unsupported(self,*args,**kwargs):raise UnsupportedOperationError('Outside experiment profile')
    on_message_send_stream=unsupported;on_subscribe_to_task=unsupported
    on_create_task_push_notification_config=unsupported;on_get_task_push_notification_config=unsupported
    on_list_task_push_notification_configs=unsupported;on_delete_task_push_notification_config=unsupported;on_get_extended_agent_card=unsupported
    def resume(self):
        for tid,body in self.db.execute('SELECT id,body FROM tasks').fetchall():
            if json.loads(body)['status']['state'] not in TERMINAL:self.workers[tid]=asyncio.create_task(self.work(tid))

async def main(args):
    directory=Path(args.directory).resolve()
    if not directory.is_relative_to(HERE/'evidence'):raise ValueError('Isolated experiment directory required')
    for _ in range(500):
        if (directory/'launch-gate').exists():break
        await asyncio.sleep(.01)
    else:raise RuntimeError('No supervisor gate')
    sock=socket.socket();sock.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1);sock.bind(('127.0.0.1',args.port));sock.listen(128);sock.setblocking(False)
    base='http://127.0.0.1:'+str(sock.getsockname()[1]);tasks=Tasks(directory,args.name,base)
    card_data=card(args.name,base)
    if args.bad_card:card_data['version']='99.0.0'
    @asynccontextmanager
    async def lifespan(app):
        tasks.resume();tasks.event('service-started',endpoint=base,name=args.name)
        yield
        for task in tasks.workers.values():task.cancel()
        await asyncio.gather(*tasks.workers.values(),return_exceptions=True)
        tasks.db.close()
    async def artifact(request):
        tid=request.path_params['tid'];row=tasks.db.execute('SELECT content FROM artifacts WHERE taskId=?',(tid,)).fetchone()
        if not row:return Response(status_code=404)
        return Response(row[0],media_type='application/json')
    app=Starlette(routes=[*create_agent_card_routes(ParseDict(card_data,p.AgentCard())),*create_jsonrpc_routes(tasks,'/rpc',enable_v0_3_compat=False),Route('/artifacts/{tid}',artifact)],lifespan=lifespan)
    class Boundary:
        def __init__(self,app):self.app=app;self.dropped=set()
        async def __call__(self,scope,receive,send):
            if scope['type']!='http':return await self.app(scope,receive,send)
            headers=dict(scope['headers'])
            if headers.get(b'authorization')!=('Bearer '+SECRET).encode():
                return await Response(status_code=401)(scope,receive,send)
            chunks=[]
            while True:
                part=await receive();chunks.append(part.get('body',b''))
                if not part.get('more_body'):break
            body=b''.join(chunks);payload={}
            if body:
                try:payload=json.loads(body)
                except Exception:pass
            method=payload.get('method');params=payload.get('params',{});mode=''
            if method=='SendMessage':mode=params.get('message',{}).get('parts',[{}])[0].get('data',{}).get('mode','')
            if method=='GetTask':
                try:mode=json.loads(tasks.db.execute('SELECT args FROM tasks WHERE id=?',(params.get('id'),)).fetchone()[0])['mode']
                except (TypeError,KeyError):pass
            jsonl(directory/'http.jsonl',{'direction':'request','path':scope['path'],'headers':{k.decode():v.decode() for k,v in scope['headers']},'body':payload})
            consumed=False
            async def replay():
                nonlocal consumed
                if not consumed:consumed=True;return {'type':'http.request','body':body,'more_body':False}
                await asyncio.sleep(60);return {'type':'http.disconnect'}
            key=(method,params.get('message',{}).get('messageId','submit') if method=='SendMessage' else params.get('id'))
            drop=(method=='SendMessage' and mode=='lost-submit' or method=='GetTask' and mode=='query-drop-once') and key not in self.dropped
            buffer=[]
            async def capture(message):buffer.append(message)
            await self.app(scope,replay,capture)
            if drop:
                self.dropped.add(key);tasks.event('wire-response-dropped',method=method)
                # Real HTTP disconnect: advertise a body then terminate it early.
                await send({'type':'http.response.start','status':200,'headers':[(b'content-length',b'10000')]})
                await send({'type':'http.response.body','body':b'','more_body':False});return
            if mode=='protocol-error' and method=='GetTask':
                return await Response(b'not-json',media_type='application/json')(scope,replay,send)
            for msg in buffer:
                if msg['type']=='http.response.body' and msg.get('body'):
                    try:jsonl(directory/'http.jsonl',{'direction':'response','path':scope['path'],'body':json.loads(msg['body'])})
                    except (ValueError,UnicodeDecodeError):pass
                await send(msg)
    server=uvicorn.Server(uvicorn.Config(Boundary(app),log_level='critical',access_log=False,lifespan='on',timeout_graceful_shutdown=1))
    worker=asyncio.create_task(server.serve(sockets=[sock]))
    while not server.started:
        if worker.done():await worker
        await asyncio.sleep(.01)
    write(directory/'ready.json',{'endpoint':base,'pid':os.getpid(),'name':args.name,'version':'0.1.0'})
    await worker
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--directory',required=True);parser.add_argument('--name',required=True);parser.add_argument('--port',type=int,default=0);parser.add_argument('--bad-card',action='store_true')
    asyncio.run(main(parser.parse_args()))
