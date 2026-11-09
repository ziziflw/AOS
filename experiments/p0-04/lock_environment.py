"""Freeze the resolved artifacts before executing SDK code; retain provenance."""
import json,hashlib,importlib.metadata as md
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
def main():
    report=json.loads((HERE/'installation-report.json').read_text(encoding='utf-8'))
    lines=[]; inventory=[]
    for row in report['install']:
        m=row['metadata']; name=m['name']; version=m['version']; sha=row['download_info']['archive_info']['hashes']['sha256']
        lines.append(f'{name}=={version} --hash=sha256:{sha}')
        inventory.append({'name':name,'version':version,'artifact':row['download_info'],
            'license':m.get('license_expression') or m.get('license') or m.get('classifier',[]),
            'projectUrls':m.get('project_url',[]),'reason':'official MCP SDK direct dependency or its transitive runtime dependency; no extras'})
    (HERE/'requirements.lock').write_text('\n'.join(sorted(lines,key=str.lower))+'\n',encoding='utf-8')
    (HERE/'dependency-inventory.json').write_text(json.dumps(inventory,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    target=HERE/'baseline-manifest.json'
    if not target.exists():
        files=[p for p in ROOT.rglob('*') if p.is_file() and HERE not in p.parents and '__pycache__' not in p.parts]
        baseline={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
        target.write_text(json.dumps(baseline,indent=2)+'\n',encoding='utf-8')
    print(f'Locked {len(lines)} exact runtime artifacts; retained pre-P0-04 baseline.')
if __name__=='__main__': main()
