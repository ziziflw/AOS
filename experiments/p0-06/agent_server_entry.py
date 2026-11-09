"""Original official A2A SDK service, independent process; owned evidence root shim."""
import argparse,asyncio,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'p0-05'));sys.path.insert(0,str(HERE.parent/'p0-03'))
import agent_service
agent_service.HERE=HERE
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--directory',required=True);p.add_argument('--name',required=True);p.add_argument('--port',type=int,default=0);p.add_argument('--bad-card',action='store_true')
    asyncio.run(agent_service.main(p.parse_args()))
