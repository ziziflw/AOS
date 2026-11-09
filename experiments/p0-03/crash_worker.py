"""Owned synthetic child process: exits at an exact transaction boundary."""
from pathlib import Path
import asyncio, os, sys
from common import write
from contracts import SchemaClient
from fixtures import ROOT,FIX
from harness import Session

async def main(directory,mode):
    v=SchemaClient(ROOT/"research/02-node-contracts/schemas/contract.schema.json",FIX/"catalog.json")
    def fault(stage,event):
        match=(mode=="after-success" and stage=="after_commit" and event.get("kind")=="node-terminal" and event.get("key")=="main/A" and event.get("state")=="succeeded")
        match=match or (mode=="during-success" and stage=="before_commit" and event.get("kind")=="node-terminal" and event.get("key")=="main/A" and event.get("state")=="succeeded")
        match=match or (mode=="waiting-approval" and stage=="after_commit" and event.get("kind")=="approval-requested")
        if match:
            write(Path(directory)/"fault-injection.json",{"mode":mode,"stage":stage,"event":event,"exitCode":73})
            os._exit(73)
    session=Session(directory,v,recover=True,hook=fault)
    try: await session.runtime.drive()
    finally: await session.close(); v.close()
    raise SystemExit("Fault point was not reached")
if __name__=="__main__":
    asyncio.run(main(sys.argv[1],sys.argv[2]))

