import json, os, shutil, tomllib
from pathlib import Path
def collect(source,out):
    rows=[]
    def add(ecosystem,name,version,license,folder):
        files=[]
        if folder and folder.is_dir():
            for f in folder.iterdir():
                if f.is_file() and f.name.upper().startswith(('LICENSE','LICENCE','COPYING','NOTICE','COPYRIGHT')):
                    dst=out/'licenses'/ecosystem/(name.replace('/','_')+'-'+version)/f.name
                    dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(f,dst);files.append(dst.relative_to(out).as_posix())
        rows.append(dict(ecosystem=ecosystem,name=name,version=version,license=license,files=files))
    for key,v in json.loads((source/'frontend/package-lock.json').read_text())['packages'].items():
        if key and not v.get('dev'):add('npm',key.split('node_modules/')[-1],v['version'],v.get('license'),source/'frontend'/key)
    registry=Path(os.environ.get('CARGO_HOME',Path.home()/'.cargo'))/'registry/src'
    for item in tomllib.loads((source/'host/Cargo.lock').read_text())['package']:
        name=item['name'];version=item['version'];folder=next(registry.glob('*/'+name+'-'+version),None)
        if folder:
            pkg=tomllib.loads((folder/'Cargo.toml').read_text(encoding='utf-8'))['package'];add('cargo',name,version,pkg.get('license'),folder)
    (out/'licenses/native-web-manifest.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
