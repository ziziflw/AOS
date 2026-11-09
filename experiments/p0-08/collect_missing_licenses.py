"""Read exact-version PyPI source archives as data; never execute packaging scripts."""
import hashlib,io,json,tarfile,urllib.request,urllib.parse
from pathlib import Path,PurePosixPath
from boot import HERE,write
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
rows=[]
for name,version in [('aiologic','0.17.1'),('culsans','0.11.0')]:
    meta=json.load(opener.open(f'https://pypi.org/pypi/{name}/{version}/json',timeout=20))
    artifact=next(x for x in meta['urls'] if x['packagetype']=='sdist')
    assert urllib.parse.urlparse(artifact['url']).hostname=='files.pythonhosted.org'
    data=opener.open(artifact['url'],timeout=20).read();sha=hashlib.sha256(data).hexdigest();assert sha==artifact['digests']['sha256']
    dest=HERE/'source-archives'/artifact['filename'];dest.parent.mkdir(exist_ok=True);dest.write_bytes(data)
    files=[]
    with tarfile.open(fileobj=io.BytesIO(data),mode='r:*') as tar:
        for member in tar:
            if not member.isfile() or not any(k in PurePosixPath(member.name).name.lower() for k in ('license','notice','copying','copyright','isc.txt','cc-by-')):continue
            parts=PurePosixPath(member.name).parts[1:]
            assert parts and '..' not in parts
            p=HERE/'third-party'/name/'sdist'/Path(*parts);p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(tar.extractfile(member).read());files.append(str(p.relative_to(HERE)))
    assert files
    rows.append({'name':name,'version':version,'url':artifact['url'],'sha256':sha,'files':files,'executed':False})
write(HERE/'evidence/supplemental-source-licenses.json',rows)
print(json.dumps(rows,indent=2))
