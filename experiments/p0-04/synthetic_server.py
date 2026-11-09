"""Trusted independent SDK MCP server; all data/effects stay in its case directory."""
import argparse,asyncio,json,os,sqlite3,sys,time,subprocess
from pathlib import Path
if __name__=='__main__' and '--idle-child' in sys.argv:
    time.sleep(60); raise SystemExit(0)
from bootstrap import HERE,read,PROTOCOL
from tool_specs import SPECS,descriptor
import anyio
from mcp.server import Server,NotificationOptions
from mcp.server.stdio import stdio_server
from mcp import types
from mcp.shared.exceptions import McpError

async def main(args):
    directory=Path(args.directory).resolve()
    if not directory.is_relative_to(HERE/'evidence'): raise ValueError('Only isolated evidence directory allowed')
    # Parent assigns its Windows Job before opening this gate, preventing child creation before ownership.
    gate=directory/'launch-gate'
    for _ in range(500):
        if gate.exists(): break
        await asyncio.sleep(.01)
    else: raise RuntimeError('Missing owning-process gate')
    db=sqlite3.connect(directory/'server-ledger.sqlite',isolation_level=None)
    db.execute('PRAGMA journal_mode=WAL'); db.execute('PRAGMA synchronous=FULL')
    db.execute('CREATE TABLE IF NOT EXISTS records(seq INTEGER PRIMARY KEY,kind TEXT,body TEXT)')
    def record(kind,**body):
        db.execute('INSERT INTO records(kind,body) VALUES(?,?)',(kind,json.dumps({'pid':os.getpid(),'time':time.time(),**body},ensure_ascii=False)))
    record('started',mode=args.mode)
    if args.mode=='spawn-child':
        child=subprocess.Popen([sys.executable,'-B',str(Path(__file__).resolve()),'--idle-child'],creationflags=subprocess.CREATE_NO_WINDOW)
        record('child-started',childPid=child.pid)
    if args.mode=='init-exit': os._exit(61)
    if args.mode=='slow-init': await anyio.sleep(1)
    server=Server('aos-p0-04-synthetic',version='0.1.0')
    @server.list_tools()
    async def tools():
        result=[descriptor(n) for n in SPECS]
        if args.mode=='schema-drift': result[0]['inputSchema']['required']=[]
        return [types.Tool.model_validate(x) for x in result]
    @server.call_tool()
    async def call(name,arguments):
        meta=server.request_context.meta
        extra=meta.model_dump(by_alias=True,exclude_none=True) if meta else {}
        identity=extra.get('aos:dispatch',{})
        op=identity.get('operationId','direct-'+str(server.request_context.request_id))
        record('call-started',tool=name,arguments=arguments,dispatch=identity,requestId=server.request_context.request_id)
        if args.mode=='stdout-pollution':
            os.write(1,b'DEBUG: not a JSON-RPC message\n')
            await asyncio.sleep(.1)
        if args.mode=='call-exit': os._exit(62)
        if name=='echo_text': result={'text':arguments['text']}
        elif name=='add_numbers': result={'sum':arguments['a']+arguments['b']}
        elif name=='delayed_result':
            try:
                with anyio.CancelScope(shield=args.mode=='ignore-cancel'):
                    await anyio.sleep(arguments['delayMs']/1000)
                    result={'value':arguments['value']}
            except BaseException:
                record('handler-cancelled',operationId=op); raise
        elif name=='structured_result':
            if arguments['source']!={'resourceUri':'workspace:source/sample.txt','mediaType':'text/plain','sizeBytes':12}:
                return types.CallToolResult(content=[types.TextContent(type='text',text='Synthetic source not bound')],isError=True)
            result={'items':[{'text':arguments['query'],'source':arguments['source']}],'operationState':'confirmed'}
        elif name=='simulated_failure':
            if arguments['mode']=='retry-once':
                count=db.execute("SELECT count(*) FROM records WHERE kind='retry-seen' AND json_extract(body,'$.operationId')=?",(op,)).fetchone()[0]
                record('retry-seen',operationId=op)
                if identity.get('attemptNumber',1)>1: result={'ok':True}
                else: return types.CallToolResult(content=[types.TextContent(type='text',text='SAFE_TRANSIENT')],isError=True)
            else: return types.CallToolResult(content=[types.TextContent(type='text',text='PRESET_TOOL_FAILURE')],isError=True)
        elif name=='simulated_effect':
            record('effect-committed',operationId=op,value=arguments['value'])
            result={'value':arguments['value'],'operationId':op}
            if args.mode=='lost-response': os._exit(63)
            if args.mode=='effect-delay': await anyio.sleep(1.5)
        else: raise ValueError('Unknown tool')
        record('call-finished',tool=name,operationId=op,result=result)
        if args.mode=='bad-output': result={'wrong':123}
        # Direct result intentionally lets the bad-output fault reach the client validator.
        return types.CallToolResult(content=[types.TextContent(type='text',text=json.dumps(result,ensure_ascii=False))],structuredContent=result)
    normal=server.request_handlers[types.CallToolRequest]
    async def protocol_fault(req):
        if req.params.name not in SPECS: raise McpError(types.ErrorData(code=-32602,message='Unknown tool'))
        if req.params.name=='simulated_failure' and req.params.arguments.get('mode')=='protocol-error':
            raise McpError(types.ErrorData(code=-32602,message='Injected JSON-RPC error'))
        return await normal(req)
    server.request_handlers[types.CallToolRequest]=protocol_fault
    if args.mode=='bad-version':
        import mcp.server.session
        mcp.server.session.SUPPORTED_PROTOCOL_VERSIONS[:]=['1900-01-01']
        types.LATEST_PROTOCOL_VERSION='1900-01-01'
    print('Synthetic MCP server pid='+str(os.getpid()),file=sys.stderr,flush=True)
    async with stdio_server() as (reader,writer):
        await server.run(reader,writer,server.create_initialization_options())
    record('normal-exit'); db.close()

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--directory',required=True); p.add_argument('--mode',default='normal')
    asyncio.run(main(p.parse_args()))
