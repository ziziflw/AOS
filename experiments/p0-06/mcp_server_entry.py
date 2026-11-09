"""Reuse the original independent SDK server; change only its owned evidence root."""
import argparse,asyncio,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'p0-04'));sys.path.insert(0,str(HERE.parent/'p0-03'))
import synthetic_server
synthetic_server.HERE=HERE
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--directory',required=True);p.add_argument('--mode',default='normal');a=p.parse_args()
    if a.mode not in ('normal','spawn-child'):raise SystemExit('MODE_DENIED')
    asyncio.run(synthetic_server.main(a))
