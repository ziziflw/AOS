import asyncio,importlib.util
from pathlib import Path
from datetime import datetime,timezone
from boot import HERE
s=importlib.util.spec_from_file_location('p008_endpoint',HERE/'executor.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
async def main():
    out=HERE/'evidence'/('smoke-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    session=m.Session(out,m.profile.sample()['workflow'])
    try:
        state=await session.runtime.drive();session.export();print(state['state'],{k:n.get('error') for k,n in state['nodes'].items()})
    finally:
        await session.runtime.close();await session.registry.close();session.release_resources();session.store.close();session.system.close()
asyncio.run(main())
