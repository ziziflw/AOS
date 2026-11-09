"""Controlled owning-process exits: before dispatch, in flight, after durable result."""
import asyncio,os,sys
from pathlib import Path
from bootstrap import ROOT,HERE,write
from cases import FIX
from contracts import SchemaClient
from integration import Session
async def main():
    directory=Path(sys.argv[1]); mode=sys.argv[2]
    def crash(stage,event):
        wanted=(mode=='before-call' and event['kind']=='node-ready' or mode=='after-call' and event['kind']=='node-terminal' and event.get('state')=='succeeded')
        if stage=='after_commit' and event.get('key')=='main/tool' and wanted:
            write(directory/'fault-injection.json',{'mode':mode,'stage':stage,'event':event,'exit':74}); os._exit(74)
    v=SchemaClient(ROOT/'research/02-node-contracts/schemas/contract.schema.json',FIX/'catalog.json')
    s=Session(directory,v,recover=True,hook=crash)
    if mode=='during-call':
        task=asyncio.create_task(s.runtime.drive())
        deadline=asyncio.get_running_loop().time()+15
        while asyncio.get_running_loop().time()<deadline:
            rows=s.ledgers()
            if any(r['kind']=='effect-committed' for r in rows):
                write(directory/'fault-injection.json',{'mode':mode,'stage':'external-effect-committed-response-pending','exit':74}); os._exit(74)
            await asyncio.sleep(.005)
        raise RuntimeError('Injection not reached')
    await s.runtime.drive(); raise RuntimeError('Injection not reached')
if __name__=='__main__': asyncio.run(main())
