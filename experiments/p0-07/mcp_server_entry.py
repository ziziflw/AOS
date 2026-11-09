"""Same reviewed P0-04 service, restricted to P0-07's evidence root."""
import argparse,asyncio
from boot import HERE
import synthetic_server
synthetic_server.HERE=HERE
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--directory',required=True);p.add_argument('--mode',default='normal')
    asyncio.run(synthetic_server.main(p.parse_args()))
