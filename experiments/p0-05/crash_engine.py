"""Controlled executor crash; Agent services remain owned by the test supervisor."""
import asyncio,os,sys
from pathlib import Path
from bootstrap_agent import ROOT,write
from agent_cases import FIX
from agent_integration import Session
from contracts import SchemaClient
async def main():
    directory=Path(sys.argv[1])
    def hook(stage,event):
        if stage=='after_commit' and event['kind']=='agent-observed' and event.get('remoteState')=='TASK_STATE_WORKING':
            write(directory/'fault-injection.json',{'stage':stage,'event':event,'exit':85,'agentLifetime':'independent supervisor'})
            os._exit(85)
    v=SchemaClient(ROOT/'research/02-node-contracts/schemas/contract.schema.json',FIX/'catalog.json')
    s=Session(directory,v,recover=True,hook=hook)
    await s.runtime.drive();s.export();raise RuntimeError('Crash point not reached')
if __name__=='__main__':asyncio.run(main())
