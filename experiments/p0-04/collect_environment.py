"""Record installed provenance and copy packaged license notices, not legal clearance."""
import hashlib,json,importlib.metadata as md,platform,sys
from pathlib import Path
from bootstrap import HERE,write,read,SDK,PROTOCOL
from mcp import types
from mcp.shared.version import SUPPORTED_PROTOCOL_VERSIONS
def main():
    inventory=read(HERE/'dependency-inventory.json'); notices=[]
    for row in inventory:
        dist=md.distribution(row['name'])
        if dist.version!=row['version']: raise RuntimeError('Installed dependency drift')
        for f in dist.files or []:
            label=str(f).replace('\\','/')
            if '.dist-info/' in label and any(x in f.name.lower() for x in ('license','copying','notice')):
                source=Path(dist.locate_file(f))
                if source.is_file():
                    target=HERE/'licenses'/row['name']/Path(label.split('.dist-info/',1)[1]);target.parent.mkdir(parents=True,exist_ok=True)
                    target.write_bytes(source.read_bytes());notices.append(target.relative_to(HERE).as_posix())
    wheels={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (HERE/'wheelhouse').glob('*.whl')}
    expected={r['download_info']['archive_info']['hashes']['sha256'] for r in read(HERE/'installation-report.json')['install']}
    result={'python':sys.version,'platform':platform.platform(),'MCPProtocol':PROTOCOL,'SDK':md.version('mcp'),
            'SDKLatestProtocolConstant':types.LATEST_PROTOCOL_VERSION,'SDKSupportedProtocols':SUPPORTED_PROTOCOL_VERSIONS,
            'dependencyCount':len(inventory),'wheels':wheels,'wheelHashesMatchInstallReport':set(wheels.values())==expected,
            'packagedLicenseNotices':notices,'licensesWithoutPackagedNotice':[r['name'] for r in inventory if not any('/'+r['name']+'/' in p for p in notices)],
            'scope':'CPython 3.12 Windows x64 artifacts; not Linux/macOS wheels or production distribution legal review'}
    write(HERE/'environment-evidence.json',result);print(json.dumps({k:result[k] for k in ('SDK','dependencyCount','wheelHashesMatchInstallReport')}))
if __name__=='__main__': main()
