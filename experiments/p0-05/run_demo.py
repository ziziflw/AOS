import argparse,asyncio
from datetime import datetime,timezone
from bootstrap_agent import HERE,ROOT
from agent_cases import build,FIX
from agent_integration import Session
from service_host import ServiceHost
from contracts import SchemaClient
async def main(args):
    build();directory=HERE/'evidence'/('demo-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));directory.mkdir(parents=True)
    hosts={};v=SchemaClient(ROOT/'research/02-node-contracts/schemas/contract.schema.json',FIX/'catalog.json');s=None
    try:
        for name in (('agentA','agentB') if args.parallel else ('agentA',)):
            hosts[name]=await ServiceHost(directory/name,name).start()
        s=Session(directory/'workflow',v,hosts,parallel=args.parallel,skill='effect' if args.effect else 'echo')
        state=await s.runtime.drive()
        if args.approve_simulated:
            for a in state['approvals'].values():
                if a['status']=='pending':s.runtime.approve(a['id'],a['fingerprint'])
            state=await s.runtime.drive()
        s.export();print('state='+state['state']);print('evidence='+str(directory))
    finally:
        if s:await s.close()
        for host in hosts.values():await host.close()
        v.close()
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--parallel',action='store_true');p.add_argument('--effect',action='store_true');p.add_argument('--approve-simulated',action='store_true');asyncio.run(main(p.parse_args()))
