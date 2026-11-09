"""Inspect wheels without importing them; retain bundled legal material and hashes."""
import email,hashlib,json,zipfile
from pathlib import Path
HERE=Path(__file__).resolve().parent
rows=[]
for p in sorted((HERE/'wheelhouse').glob('*.whl')):
    with zipfile.ZipFile(p) as z:
        names=z.namelist();m=email.message_from_bytes(z.read(next(n for n in names if n.endswith('.dist-info/METADATA'))))
        hooks=[n for n in names if n.endswith('.pth') or '/scripts/' in n or n.endswith(('sitecustomize.py','usercustomize.py'))]
        legal=[n for n in names if any(k in n.lower().split('/')[-1] for k in ('license','notice','copying'))]
        for n in legal:
            dest=HERE/'third-party'/m['Name']/n;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(z.read(n))
        rows.append({'name':m['Name'],'version':m['Version'],'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),
                     'license':m.get('License-Expression') or m.get('License') or next((c for c in m.get_all('Classifier',[]) if c.startswith('License ::')),None),'urls':m.get_all('Project-URL'),
                     'requires':m.get_all('Requires-Dist',[]),'hooks':hooks,'legal':legal,
                     'native':[n for n in names if n.endswith(('.pyd','.dll'))]})
(HERE/'evidence/dependency-review.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
assert all(not r['hooks'] or (r['name']=='pywin32' and r['version']=='312' and [n for n in r['hooks'] if n.endswith('.pth')]==['pywin32.pth']) for r in rows), 'Unexpected startup hook'
(HERE/'sdk-requirements.lock').write_text('\n'.join(f"{r['name']}=={r['version']} --hash=sha256:{r['sha256']}" for r in rows)+'\n')
print(json.dumps([{'name':r['name'],'version':r['version'],'license':r['license'],'legalFiles':len(r['legal']),'native':r['native']} for r in rows],indent=2))
