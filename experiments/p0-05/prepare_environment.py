"""Freeze SDK artifacts and preserve pre-P0-05 source/evidence hashes before integration."""
import hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
def main():
    report=json.loads((HERE/'installation-report.json').read_text(encoding='utf-8'))
    rows=[];lock=[]
    for row in report['install']:
        m=row['metadata'];sha=row['download_info']['archive_info']['hashes']['sha256']
        lock.append(f"{m['name']}=={m['version']} --hash=sha256:{sha}")
        rows.append({'name':m['name'],'version':m['version'],'artifact':row['download_info'],
            'projectUrls':m.get('project_url',[]),'license':m.get('license_expression') or m.get('license') or m.get('classifier',[]),
            'reason':'A2A SDK/http-server dependency, or fixed local uvicorn/pywin32/schema verification dependency; no grpc/sql/agent framework extras'})
    (HERE/'requirements.lock').write_text('\n'.join(sorted(lock,key=str.lower))+'\n',encoding='utf-8')
    (HERE/'dependency-inventory.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    target=HERE/'baseline-manifest.json'
    if not target.exists():
        files=[p for p in ROOT.rglob('*') if p.is_file() and HERE not in p.parents and not {'.venv','__pycache__'}.intersection(p.parts)]
        target.write_text(json.dumps({p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files},indent=2)+'\n',encoding='utf-8')
    print('Locked '+str(len(lock))+' exact artifacts; baseline retained.')
if __name__=='__main__': main()
