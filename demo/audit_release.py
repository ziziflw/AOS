from pathlib import Path
import hashlib,json,zipfile,re,sqlite3
D=Path(__file__).resolve().parent
Z=D.parent/'dist/AOS-Demo-v0.1.0-win-x64.zip';folder=Z.with_suffix('');root=Path((D/'latest-qa.txt').read_text().strip())/folder.name/'app/experiments/p0-08/evidence/qa'
with zipfile.ZipFile(Z) as archive:
 assert archive.testzip() is None
 items=[i for i in archive.infolist() if not i.is_dir()];bad=[];total=0
 for item in items:
  f=D.parent/'dist'/item.filename;assert f.stat().st_size==item.file_size
  payload=archive.read(item);assert hashlib.sha256(payload).digest()==hashlib.sha256(f.read_bytes()).digest();total+=item.file_size
  rel=Path(item.filename);parts=set(rel.parts)
  if parts & {'evidence','workspace','node_modules','target','__pycache__','.git'} or rel.suffix.lower() in {'.sqlite','.sqlite3','.log','.gguf','.safetensors','.pyc'}:bad.append(item.filename)
  if re.search(rb'fixture-secret-[a-f0-9]{32}',payload):bad.append(item.filename)
 assert not bad,bad
states=[]
for path in root.glob('runs/*/run.sqlite'):
 db=sqlite3.connect(path);assert db.execute('pragma integrity_check').fetchone()[0]=='ok';s=json.loads(db.execute('select state from snapshot').fetchone()[0]);db.close();states.append(dict(runId=s['runId'],state=s['state'],mcpLedgers=len(list(path.parent.glob('mcp-*/server-ledger.sqlite')))))
report=dict(zipBytes=Z.stat().st_size,folderBytes=total,sha256=hashlib.file_digest(Z.open('rb'),'sha256').hexdigest(),zipFiles=len(items),releaseRuns=states,normalWindow=json.loads((D/'normal-window.json').read_text(encoding='utf-8-sig')),regressions=(D/'regression-status.txt').read_text().splitlines(),excludedContentFindings=bad)
(D/'release-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(total,len(items),states)
