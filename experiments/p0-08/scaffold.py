"""Copy only reviewed P0-07 UI/host glue. C1/D2/D3 remain imports."""
from pathlib import Path
import shutil
H=Path(__file__).resolve().parent;P=H.parent/'p0-07'
for folder,patterns in [('frontend',['*.json','*.js','*.html','src/*']),('host',['Cargo.toml','Cargo.lock','build.rs','tauri.conf.json','capabilities/*','src/*'])]:
    for pattern in patterns:
        for src in (P/folder).glob(pattern):
            if not src.is_file():continue
            dst=H/folder/src.relative_to(P/folder);dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
            if dst.suffix in ('.rs','.toml','.json','.js','.vue','.html') or dst.name=='Cargo.lock':
                text=dst.read_text(encoding='utf-8').replace('p007','p008').replace('p0-07','p0-08').replace('P0-07','P0-08').replace('9237','9238')
                if dst.name=='lib.rs':text=text.replace('self.root.parent().unwrap().join("p0-06/.venv/Scripts/python.exe")','self.root.join(".venv/Scripts/python.exe")')
                dst.write_text(text,encoding='utf-8')
for name in ('windows_adapter.py','mcp_server_entry.py'):
    shutil.copy2(P/name,H/name)
# A separate installation path, unchanged packages/lock. Never modify P0-07 node_modules.
shutil.copytree(P/'frontend/node_modules',H/'frontend/node_modules',dirs_exist_ok=True)
print('Scaffolded reviewed host/editor; no scheduler copied')
