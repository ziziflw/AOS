"""Official SDK ClientSession over a strict, owned stdio transport. No retries."""
import asyncio,json,time
from datetime import timedelta
from pathlib import Path
import anyio
from mcp import ClientSession,types
from mcp.shared.message import SessionMessage
from mcp.shared.exceptions import McpError
from jsonschema import Draft202012Validator
from bootstrap import write,digest,ContractError,OutcomeError,PROTOCOL
from process_host import ProcessHost
from tool_specs import descriptor,signature

def specific_error(exc):
    if isinstance(exc,ContractError): return exc
    for child in getattr(exc,'exceptions',[]):
        found=specific_error(child)
        if found: return found
    return None

class MCPClient:
    def __init__(self,directory,launch,allowed):
        self.dir=Path(directory); self.host=ProcessHost(directory,launch); self.allowed=set(allowed)
        self.tools={}; self.request_ids={}; self.stopping=asyncio.Event(); self.failed=asyncio.Event(); self.error=None
        self.inflight=False; self.owner=None; self.closed=False; self.session=None
    def trace(self,direction,message):
        with (self.dir/'protocol.jsonl').open('a',encoding='utf-8') as f:
            f.write(json.dumps({'direction':direction,'time':time.time(),'message':message},ensure_ascii=False,allow_nan=False)+'\n')
    def fail(self,code,detail=''):
        if not self.error:
            self.error=ContractError(code,detail); self.failed.set()
            self.host.record('transport-failure',code=code,detail=detail)
    async def _reader(self,send):
        try:
            while True:
                raw=await asyncio.to_thread(self.host.p.stdout.readline,1048577)
                if not raw:
                    if not self.stopping.is_set(): self.fail('SERVER_DISCONNECTED')
                    break
                try:
                    if len(raw)>1048576 or not raw.endswith(b'\n'): raise ValueError('Oversized or incomplete frame')
                    text=raw.decode('utf-8',errors='strict')
                    data=json.loads(text,parse_constant=lambda x:(_ for _ in ()).throw(ValueError(x)))
                    message=types.JSONRPCMessage.model_validate(data)
                except Exception as exc:
                    self.trace('invalid-stdout',{'raw':raw[:1000].decode('utf-8',errors='replace')})
                    self.fail('PROTOCOL_STDOUT_CORRUPT',str(exc)); self.host.kill_owned('protocol-corruption'); break
                self.trace('server-to-client',data)
                await send.send(SessionMessage(message))
        except (OSError,ValueError,anyio.ClosedResourceError,anyio.BrokenResourceError) as exc:
            if not self.stopping.is_set(): self.fail('SERVER_DISCONNECTED',str(exc))
        finally: await send.aclose()
    async def _writer(self,receive):
        try:
            async for item in receive:
                data=item.message.model_dump(mode='json',by_alias=True,exclude_none=True)
                if data.get('method')=='tools/call':
                    identity=data.get('params',{}).get('_meta',{}).get('aos:dispatch',{})
                    self.request_ids[identity.get('attemptId')]=data['id']
                self.trace('client-to-server',data)
                payload=(json.dumps(data,ensure_ascii=False,allow_nan=False,separators=(',',':'))+'\n').encode('utf-8')
                self.host.p.stdin.write(payload); self.host.p.stdin.flush()
        except (OSError,ValueError,anyio.ClosedResourceError,anyio.BrokenResourceError) as exc:
            if not self.stopping.is_set(): self.fail('SERVER_DISCONNECTED',str(exc))
    async def _owner(self,ready):
        workers=[]
        try:
            self.host.start()
            incoming,reader=anyio.create_memory_object_stream(16)
            writer,outgoing=anyio.create_memory_object_stream(16)
            workers=[asyncio.create_task(self._reader(incoming)),asyncio.create_task(self._writer(outgoing))]
            async with ClientSession(reader,writer,read_timeout_seconds=timedelta(seconds=3)) as session:
                self.session=session
                initialized=await session.initialize()
                write(self.dir/'initialize.json',initialized.model_dump(mode='json',by_alias=True,exclude_none=True))
                if initialized.protocolVersion!=PROTOCOL: raise ContractError('PROTOCOL_VERSION_MISMATCH',initialized.protocolVersion)
                if initialized.serverInfo.name!='aos-p0-04-synthetic' or initialized.serverInfo.version!='0.1.0': raise ContractError('SERVER_IDENTITY_DRIFT')
                if initialized.capabilities.tools is None: raise ContractError('TOOLS_CAPABILITY_MISSING')
                found=await session.list_tools()
                if found.nextCursor is not None: raise ContractError('PAGINATION_UNIMPLEMENTED')
                records=[t.model_dump(mode='json',by_alias=True,exclude_none=True) for t in found.tools]
                write(self.dir/'tools-discovered.json',records)
                self.tools={d['name']:d for d in records}
                if len(self.tools)!=len(records): raise ContractError('DUPLICATE_TOOL')
                for name in self.allowed:
                    if name not in self.tools: raise ContractError('TOOL_UNAVAILABLE',name)
                    if signature(self.tools[name])!=signature(descriptor(name)): raise ContractError('TOOL_SCHEMA_DRIFT',name)
                ready.set_result(True)
                await self.stopping.wait()
        except BaseException as exc:
            if not ready.done(): ready.set_exception(self.error or specific_error(exc) or ContractError('INITIALIZATION_FAILED',str(exc)))
            elif not self.stopping.is_set(): self.fail('SESSION_FAILED',str(exc))
        finally:
            self.stopping.set()
            await self.host.close()
            for worker in workers:
                if not worker.done(): worker.cancel()
            if workers: await asyncio.gather(*workers,return_exceptions=True)
    async def open(self):
        ready=asyncio.get_running_loop().create_future()
        ready.add_done_callback(lambda f: f.exception() if not f.cancelled() else None)
        self.owner=asyncio.create_task(self._owner(ready))
        try: await asyncio.wait_for(asyncio.shield(ready),5)
        except BaseException:
            await self.close(); raise
        return self
    async def close(self):
        if self.closed:
            await self.host.close(); return
        self.closed=True; self.stopping.set()
        if self.owner:
            try: await asyncio.wait_for(asyncio.shield(self.owner),5)
            except TimeoutError:
                self.host.kill_owned('owner-close-timeout'); self.owner.cancel()
                await asyncio.gather(self.owner,return_exceptions=True)
        else: await self.host.close()
    async def call(self,name,arguments,identity,*,cancel=None,timeout=2,effect='none'):
        if self.inflight: raise ContractError('ONE_CALL_PER_CONNECTION_ONLY')
        if self.closed or self.error: raise self.error or ContractError('SESSION_CLOSED')
        if name not in self.allowed: raise ContractError('TOOL_PERMISSION_DENIED',name)
        if name not in self.tools: raise ContractError('TOOL_UNAVAILABLE',name)
        Draft202012Validator(self.tools[name]['inputSchema']).validate(arguments)
        if cancel is not None and cancel.is_set(): raise OutcomeError('MCP_CANCEL_BEFORE_CALL',side_effect='unknown')
        self.inflight=True
        task=asyncio.create_task(self.session.call_tool(name,arguments,meta={'aos:dispatch':identity}))
        lost=asyncio.create_task(self.failed.wait()); stopped=asyncio.create_task(cancel.wait()) if cancel else None
        try:
            done,_=await asyncio.wait([task,lost,*([stopped] if stopped else [])],timeout=timeout,return_when=asyncio.FIRST_COMPLETED)
            if lost in done: raise OutcomeError(self.error.code,side_effect='unknown' if effect in ('write','unknown') else 'not-started')
            if stopped is not None and stopped in done:
                await self._cancel(identity,'user-cancel')
                raise OutcomeError('MCP_CANCEL_UNCONFIRMED',side_effect='unknown')
            if task not in done:
                await self._cancel(identity,'deadline')
                raise OutcomeError('MCP_REQUEST_TIMEOUT',side_effect='unknown' if effect in ('write','unknown') else 'not-started')
            try: result=task.result()
            except McpError as exc: raise OutcomeError('MCP_JSONRPC_ERROR',side_effect='unknown' if effect in ('write','unknown') else 'not-started') from exc
            except Exception as exc: raise OutcomeError('MCP_OUTPUT_INVALID',side_effect='unknown' if effect in ('write','unknown') else 'not-started') from exc
            raw=result.model_dump(mode='json',by_alias=True,exclude_none=True); write(self.dir/('result-'+identity['attemptId']+'.json'),raw)
            if result.isError:
                safe=effect in ('none','read') and any(getattr(x,'text','')=='SAFE_TRANSIENT' for x in result.content)
                raise OutcomeError('MCP_TOOL_ERROR',retryable=safe,side_effect='unknown' if effect in ('write','unknown') else 'not-started')
            if result.structuredContent is None: raise ContractError('MCP_STRUCTURED_CONTENT_REQUIRED')
            Draft202012Validator(self.tools[name]['outputSchema']).validate(result.structuredContent)
            return result.structuredContent
        except asyncio.CancelledError:
            await self._cancel(identity,'controller-task-cancel')
            raise OutcomeError('MCP_CANCEL_UNCONFIRMED',side_effect='unknown')
        finally:
            for t in (task,lost,stopped):
                if t and not t.done(): t.cancel()
            await asyncio.gather(*[t for t in (task,lost,stopped) if t],return_exceptions=True)
            self.inflight=False
    async def _cancel(self,identity,reason):
        rid=self.request_ids.get(identity['attemptId'])
        if rid is not None and not self.error:
            await self.session.send_notification(types.ClientNotification(types.CancelledNotification(
                method='notifications/cancelled',params=types.CancelledNotificationParams(requestId=rid,reason=reason))))
            # Only records request submission. MCP notification has no physical-stop acknowledgement.
            self.host.record('cancel-requested',requestId=rid,dispatch=identity,reason=reason)
            await asyncio.sleep(.005)
