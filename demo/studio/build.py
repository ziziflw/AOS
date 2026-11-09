from pathlib import Path
import os,subprocess,shutil
D=Path(__file__).resolve().parent
host=D/'host'
original=D.parents[1]/'experiments/p0-08/host'
for name in ('src','icons','capabilities'):
 shutil.copytree(original/name,host/name,dirs_exist_ok=True)
for name in ('Cargo.toml','Cargo.lock','build.rs','tauri.conf.json'):
 shutil.copy2(original/name,host/name)
window=host/'src/window.rs'
window.write_text(window.read_text(encoding='utf8').replace('Graphite Workbench — P0-08','Graphite Workbench — 工作台 0.1.3').replace('"response":reply','"ok":reply["ok"]'),encoding='utf8')
os.environ['CARGO_TARGET_DIR']=str(D.parent/'build/host/target')
subprocess.run(['npm.cmd','run','build','--','--outDir',str(host/'ui'),'--emptyOutDir'],cwd=D/'frontend',check=True)
os.environ['RUSTFLAGS']='--remap-path-prefix='+str(D.parents[1])+'=aos-src -C debuginfo=0 -C strip=symbols'
subprocess.run(['cargo','build','--features','window','--bin','host-window','--locked','--offline'],cwd=host,check=True)
shutil.copy2(Path(os.environ['CARGO_TARGET_DIR'])/'debug/host-window.exe',D/'workbench.exe')

