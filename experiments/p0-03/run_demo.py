"""Run a synthetic demo, leaving all inputs, events and durable state as evidence."""
import argparse, asyncio
from datetime import datetime, timezone
from contracts import SchemaClient
from fixtures import generate,FIX,ROOT,HERE
from harness import Session,inputs,approve_all
async def main(args):
    generate()
    output=HERE/"evidence"/("demo-"+datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
    v=SchemaClient(ROOT/"research/02-node-contracts/schemas/contract.schema.json",FIX/"catalog.json")
    w,r,c=inputs(args.scenario); s=Session(output,v,workflow=w,request=r,catalog_path=c)
    try:
        state=await approve_all(s.runtime) if args.approve_simulated else await s.runtime.drive()
        s.export(); print("state="+state["state"]); print("runId="+state["runId"]); print("evidence="+str(output))
    finally: await s.close(); v.close()
if __name__=="__main__":
    p=argparse.ArgumentParser(); p.add_argument("--scenario",default="serial",choices=["serial","parallel","conditional","conditional-all","effect","nullable","bad-output","a","b","c"])
    p.add_argument("--approve-simulated",action="store_true",help="Trusted test operator approves only this run's synthetic requests.")
    asyncio.run(main(p.parse_args()))

