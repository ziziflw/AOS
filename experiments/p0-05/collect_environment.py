"""SDK/OS/artifact/license record; separate from Agent execution tests."""
import hashlib,importlib.metadata as md,json,platform,sys
from pathlib import Path
from bootstrap_agent import HERE,ROOT,P03,P04,SPEC,WIRE,SDK,read,write
def main():
    inventory=read(HERE/'dependency-inventory.json');notices=[]
    for row in inventory:
        dist=md.distribution(row['name'])
        if dist.version!=row['version']:raise RuntimeError('Dependency drift')
        for f in dist.files or []:
            label=str(f).replace('\\','/')
            if '.dist-info/' in label and any(x in f.name.lower() for x in ('license','copying','notice')):
                source=Path(dist.locate_file(f))
                if source.is_file():
                    target=HERE/'licenses'/row['name']/Path(label.split('.dist-info/',1)[1]);target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(source.read_bytes());notices.append(target.relative_to(HERE).as_posix())
    wheels={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (HERE/'wheelhouse').glob('*.whl')}
    expected={r['download_info']['archive_info']['hashes']['sha256'] for r in read(HERE/'installation-report.json')['install']}
    inspected=[HERE/'.venv/Lib/site-packages/a2a'/name for name in ['client/transports/jsonrpc.py','client/transports/http_helpers.py','server/routes/jsonrpc_dispatcher.py','server/request_handlers/request_handler.py']]
    result={'specification':SPEC,'wireVersion':WIRE,'SDK':md.version('a2a-sdk'),'python':sys.version,'platform':platform.platform(),
       'dependencies':len(inventory),'wheels':wheels,'wheelHashesMatchInstallReport':set(wheels.values())==expected,'packagedLicenseNotices':notices,
       'reviewedSDKSourceHashes':{p.relative_to(HERE).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in inspected},
       'scope':'CPython3.12 Windows x64; official A2A JSON-RPC client/server; no grpc or cross-OS execution'}
    write(HERE/'environment-evidence.json',result)
    regressions={}
    for stage,path in [('p0-03',P03),('p0-04',P04)]:regressions[stage]=read(path/'evidence/latest.json')
    write(HERE/'evidence/regressions.json',regressions)
    print(json.dumps({'SDK':result['SDK'],'dependencies':result['dependencies'],'wheelHashesMatchInstallReport':result['wheelHashesMatchInstallReport']}))
if __name__=='__main__':main()
