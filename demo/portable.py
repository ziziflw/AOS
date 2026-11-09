from pathlib import Path
import shutil,sys,zipfile,subprocess,hashlib
D=Path(__file__).resolve().parent; R=D.parent; P=R/'experiments'; S=P/'p0-08'
out=R/'dist/AOS-Demo-v0.1.0-win-x64';out.mkdir(parents=True,exist_ok=True); app=out/'app'
def cp(src,dst):
 dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
def tree(src,dst,exclude=()):
 shutil.copytree(src,dst,dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__','*.pyc',*exclude))
for i in range(3,9):
 src=P/f'p0-{i:02}'; dest=app/'experiments'/src.name
 for f in src.glob('*.py'):
  if not f.name.startswith(('test','audit','collect','scaffold','update_frontend','smoke','review_dependencies','cleanup_credentials','crash_worker')):cp(f,dest/f.name)
 for f in (src/'fixtures').glob('*.json'):
  if 'environment' not in f.name:cp(f,dest/'fixtures'/f.name)
for folder in ('schemas','examples'):
 src=R/'research/02-node-contracts'/folder
 for f in src.glob('*.json'):cp(f,app/f.relative_to(R))
dest=app/'experiments/p0-08';cp(S/'sdk-requirements.lock',dest/'sdk-requirements.lock')
base=Path(sys.base_prefix); rt=dest/'.venv'; bins=rt/'Scripts'
tree(base/'Lib',rt/'Lib',('site-packages','test','idlelib','tkinter','ensurepip','venv'));tree(base/'DLLs',rt/'DLLs')
tree(S/'.venv/Lib/site-packages',rt/'Lib/site-packages',('pip','pip-*.dist-info'))
for f in [base/'python.exe',*base.glob('*.dll'),*(rt/'Lib/site-packages/pywin32_system32').glob('*.dll')]:cp(f,bins/f.name)
(bins/'python._pth').write_text('../Lib\n../DLLs\n../Lib/site-packages\n../Lib/site-packages/win32\n../Lib/site-packages/win32/lib\n../Lib/site-packages/pythonwin\n../..\nimport site\n')
for stage,file in [('p0-04','cases.py'),('p0-04','integration.py'),('p0-08','windows_adapter.py')]:
 f=app/'experiments'/stage/file;t=f.read_text(encoding='utf-8').replace("HERE/'.venv/Scripts/python.exe'","HERE.parent/'p0-08/.venv/Scripts/python.exe'").replace("P04/'.venv/Scripts/python.exe'","P04.parent/'p0-08/.venv/Scripts/python.exe'").replace("p0-06/.venv/Scripts/python.exe","p0-08/.venv/Scripts/python.exe");f.write_text(t,encoding='utf-8')
f=dest/'executor.py';f.write_text(f.read_text(encoding='utf-8').replace("result.update(executorVersion=","result.update(sample=profile.old.sample(False),executorVersion="),encoding='utf-8')
for entry in ('executor.py','mcp_server_entry.py'):
 f=dest/entry;f.write_text("import sys, pathlib\nsys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))\n"+f.read_text(encoding='utf-8'),encoding='utf-8')
tree(S/'third-party',out/'licenses');cp(base/'LICENSE.txt',out/'licenses/Python.txt')
from notices import collect
collect(S,out)
cp(D/'build/host/target/debug/host-window.exe',app/'workbench.exe')
subprocess.run(['rustc',str(D/'launcher.rs'),'-C','opt-level=s','-o',str(out/'AOS.exe')],check=True)
(out/'README.txt').write_text('AOS Demo v0.1.0 | Windows x64\n需要 Microsoft Edge WebView2 Runtime。解压整个目录，双击 AOS.exe。首次启动会复制私有运行环境到 %LOCALAPPDATA%/AOS-Demo/v0.1.0。工作流与运行记录保存在该目录 experiments/p0-08/workspace 和 evidence。点击运行执行合成文本与 MCP Echo。',encoding='utf-8-sig')
subprocess.run([bins/'python.exe','-B','-c','import sqlite3, openai, anthropic, win32cred, mcp, a2a'],check=True)
cp(D/'local_models.py',dest/'local_models.py')
tree(base/'Lib/tkinter',rt/'Lib/tkinter');tree(base/'tcl',rt/'tcl')
f=dest/'model_profile.py'
addition="""
from local_models import read as local_settings
base_config_schema=config_schema
def config_schema(tid):
    schema=base_config_schema(tid)
    if tid in ('p08.ollama.text','p08.lmstudio.text'):
        schema['properties']['model']={'const':MODELS[tid]['provider'],'title':'本地连接'}
        schema['properties']['credentialAlias']={'const':'local:no-auth','title':'本机免密'}
    return schema
for key,name in [('ollama','Ollama'),('lmstudio','LM Studio')]:
    tid='p08.'+key+'.text'
    MODELS[tid]={**MODELS['p08.anthropic.text'],'provider':name,'apiVersion':'chat-completions-v1','synthetic':False}
    LABELS[tid]=name+' · 本地模型'
    DEFAULTS[tid]={**DEFAULTS['p08.anthropic.text'],'credentialAlias':'local:no-auth','model':name}
base_environment=environment
def environment():
    e=base_environment();e['extensions']['aos:local-connections']=local_settings();return e
"""
f.write_text(f.read_text(encoding='utf-8').replace("if __name__=='__main__':",addition+"\nif __name__=='__main__':"),encoding='utf-8')
f=dest/'executor.py'
marker="            if ctx.node['config']['credentialAlias']"
local_dispatch="""            if ctx.node['typeId'] in ('p08.ollama.text','p08.lmstudio.text'):
                from local_models import invoke
                return await invoke(ctx,self.binding['extensions']['aos:local-connections'].get(ctx.node['config']['model']),self.d1)
"""
settings_dispatch="""        if op=='load' and b.get('action') in ('local-settings','local-list','local-save'):
            import local_models as local
            action=b['action']
            if action=='local-settings':
                p007.p006.exact(b,('action',));return local.read()
            p007.p006.exact(b,('action','url') if action=='local-list' else ('action','service','url','model'))
            try:url=local.checked(b['url'])
            except (TypeError,ValueError):raise ContractError('LOCAL_ADDRESS_DENIED')
            try:ids=await asyncio.to_thread(local.models,url)
            except Exception:raise ContractError('LOCAL_SERVICE_UNAVAILABLE')
            ids=[i for i in ids if isinstance(i,str) and 0<len(i)<=256][:200]
            if action=='local-list':return ids
            if b['service'] not in local.PRESETS or b['model'] not in ids:raise ContractError('LOCAL_MODEL_UNAVAILABLE')
            settings=local.read();settings[b['service']]={'url':url,'model':b['model']}
            local.CONFIG.parent.mkdir(exist_ok=True);temp=local.CONFIG.with_suffix('.'+str(os.getpid())+'.tmp')
            write(temp,settings);temp.replace(local.CONFIG);return {'saved':True}
"""
f.write_text(f.read_text(encoding='utf-8').replace(marker,local_dispatch+marker).replace("        if op=='health':",settings_dispatch+"        if op=='health':"),encoding='utf-8')
f.write_text(f.read_text(encoding='utf-8').replace("'model_adapter.py','http_fixture.py'","'model_adapter.py','local_models.py','http_fixture.py'").replace("        if n['typeId'] not in profile.LABELS:", "        if n['typeId'].startswith('agent.') and n['typeId'] not in profile.LABELS:raise ContractError('A2A_SERVICE_UNBOUND')\n        if n['typeId'] not in profile.LABELS:"),encoding='utf-8')
subprocess.run([bins/'python.exe','-B','-c',"import sys,os,runpy;sys.path.insert(0,os.getcwd());runpy.run_module('model_profile',run_name='__main__')"],check=True,cwd=dest)
(out/'Local-model-settings.cmd').write_text('@echo off\nset "AOSROOT=%LOCALAPPDATA%\\AOS-Demo\\v0.1.0\\experiments\\p0-08"\nif not exist "%AOSROOT%\\local_models.py" (echo Start AOS.exe first. & pause & exit /b 1)\n"%AOSROOT%\\.venv\\Scripts\\python.exe" -B "%AOSROOT%\\local_models.py"\n')
with (out/'README.txt').open('a',encoding='utf-8') as doc:doc.write('\n点击左侧「本地模型连接」，选择 Ollama 或 LM Studio，测试连接并选择模型，保存后在「模型工作流场景」选择对应本地模型。模型须由用户预先加载。费用栏为实验估算。A2A 需另行绑定外部服务。\n')
z=out.parent/(out.name+'.zip')
with zipfile.ZipFile(z,'w',zipfile.ZIP_DEFLATED,compresslevel=3) as archive:
 for f in out.rglob('*'):
  if f.is_file():archive.write(f,f.relative_to(out.parent))
h=hashlib.file_digest(z.open('rb'),'sha256').hexdigest();(z.parent/(z.name+'.sha256')).write_text(h+'  '+z.name+'\n');print(z,z.stat().st_size,h)

