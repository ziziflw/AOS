import argparse,asyncio
from datetime import datetime,timezone
from bootstrap import HERE,ROOT
from cases import build,FIX,SPECS
from contracts import SchemaClient
from integration import Session
async def main(args):
    build(); directory=HERE/'evidence'/('demo-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    v=SchemaClient(ROOT/'research/02-node-contracts/schemas/contract.schema.json',FIX/'catalog.json')
    s=Session(directory,v,args.tool,args.mode)
    try:
        state=await s.runtime.drive()
        if args.approve_simulated:
            for a in state['approvals'].values():
                if a['status']=='pending': s.runtime.approve(a['id'],a['fingerprint'])
            state=await s.runtime.drive()
        s.export(); print('state='+state['state']); print('evidence='+str(directory))
    finally: await s.close(); v.close()
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--tool',choices=list(SPECS),default='structured_result');p.add_argument('--mode',default='normal')
    p.add_argument('--approve-simulated',action='store_true');asyncio.run(main(p.parse_args()))
