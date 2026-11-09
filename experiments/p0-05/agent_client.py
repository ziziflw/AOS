"""D3 protocol client: actual official A2A JSON-RPC transport, never MCP."""
import asyncio,hashlib,json,time
from pathlib import Path
from urllib.parse import urlsplit
import httpx
from google.protobuf.json_format import MessageToDict,ParseDict
from a2a.types import a2a_pb2 as p
from a2a.client.card_resolver import A2ACardResolver
from a2a.client.transports.jsonrpc import JsonRpcTransport
from a2a.utils.errors import A2AError
from bootstrap_agent import HERE,SECRET,WIRE,write,jsonl,digest,ContractError,OutcomeError
from agent_specs import card
class AgentClient:
    def __init__(self,directory,endpoint,name):
        u=urlsplit(endpoint)
        if u.scheme!='http' or u.hostname!='127.0.0.1' or u.path or not u.port:raise ContractError('NONLOCAL_AGENT_DENIED')
        self.dir=Path(directory);self.dir.mkdir(parents=True,exist_ok=True);self.endpoint=endpoint;self.name=name;self.transport=None
        async def request(req):
            try:body=json.loads(req.content) if req.content else None
            except ValueError:body={'unparsed':True}
            jsonl(self.dir/'protocol.jsonl',{'direction':'request','method':req.method,'url':str(req.url),'headers':dict(req.headers),'body':body,'time':time.time()})
        async def response(res):
            raw=await res.aread()
            try:body=json.loads(raw)
            except (ValueError,UnicodeDecodeError):body={'invalidBody':raw[:200].decode('utf-8',errors='replace')}
            jsonl(self.dir/'protocol.jsonl',{'direction':'response','status':res.status_code,'body':body,'time':time.time()})
        self.http=httpx.AsyncClient(timeout=.7,trust_env=False,follow_redirects=False,headers={'Authorization':'Bearer '+SECRET,'A2A-Version':WIRE},
            transport=httpx.AsyncHTTPTransport(retries=0),event_hooks={'request':[request],'response':[response]})
    async def open(self):
        try:
            observed=await A2ACardResolver(self.http,self.endpoint).get_agent_card()
            raw=MessageToDict(observed);write(self.dir/'agent-card.json',raw)
            expected=card(self.name,self.endpoint)
            # ProtoJSON omits default false/empty fields, so compare after identical SDK parsing.
            expected=MessageToDict(ParseDict(expected,p.AgentCard()))
            if digest(raw)!=digest(expected):raise ContractError('AGENT_CAPABILITY_DRIFT')
            self.card_digest=digest(raw);self.transport=JsonRpcTransport(self.http,observed,self.endpoint+'/rpc');return self
        except ContractError:raise
        except Exception:raise ContractError('AGENT_DISCOVERY_UNAVAILABLE') from None
    async def send(self,args,identity,message_id,context_id):
        request=ParseDict({'message':{'messageId':message_id,'contextId':context_id,'role':'ROLE_USER','parts':[{'data':args}],
            'metadata':{'aos:identity':identity}},'configuration':{'returnImmediately':True,'acceptedOutputModes':['application/json']}},p.SendMessageRequest())
        response=await self.transport.send_message(request)
        if response.WhichOneof('payload')=='message':raise ContractError('AGENT_TASK_REQUIRED')
        # SDK uses a proto oneof; an empty task must never be accepted as a task identity.
        if not response.HasField('task') or not response.task.id:raise ContractError('AGENT_TASK_REQUIRED')
        return MessageToDict(response.task)
    async def query(self,tid):return MessageToDict(await self.transport.get_task(p.GetTaskRequest(id=tid)))
    async def lookup(self,context_id):
        result=await self.transport.list_tasks(p.ListTasksRequest(context_id=context_id,include_artifacts=True,page_size=50))
        if result.next_page_token:raise ContractError('CORRELATION_LOOKUP_INCOMPLETE')
        return [MessageToDict(t) for t in result.tasks]
    async def cancel(self,tid):return MessageToDict(await self.transport.cancel_task(p.CancelTaskRequest(id=tid)))
    async def artifact(self,tid,url):
        expected=self.endpoint+'/artifacts/'+tid
        if url!=expected:raise ContractError('UNTRUSTED_ARTIFACT_LOCATION')
        response=await self.http.get(expected);response.raise_for_status()
        if len(response.content)>65536:raise ContractError('ARTIFACT_TOO_LARGE')
        return response.content
    async def close(self):await self.http.aclose()
