from pathlib import Path
import shutil
def install(dest):
    shutil.copy2(Path(__file__).with_name('task_extract.py'),dest/'task_extract.py')
    f=dest/'model_profile.py';s=f.read_text(encoding='utf8')
    extra="""
from task_extract import TYPE
LABELS[TYPE]='校验任务清单 JSON'
original_catalog=build_catalog
def build_catalog():
    catalog=original_catalog()
    write(CATALOG.parent/'catalog-0.1.2.json',catalog)
    d=deepcopy(next(v for v in catalog['nodeDefinitions'] if v['typeId']=='synth.step'))
    d.update(typeId=TYPE,configSchema=obj({}))
    catalog['nodeDefinitions'].append(d)
    return catalog
"""
    f.write_text(s.replace("if __name__=='__main__':",extra+"\nif __name__=='__main__':"),encoding='utf8')
    f=dest/'executor.py';s=f.read_text(encoding='utf8').replace('import model_profile as profile','import json, re, task_extract\nimport model_profile as profile')
    s=s.replace("if tid in ('p08.json-text','p08.join')","if tid in ('p08.json-text','p08.join',task_extract.TYPE)")
    s=s.replace("        if ctx.node['typeId']=='p08.json-text':","        if ctx.node['typeId']==task_extract.TYPE:return Result({'out':json.dumps(task_extract.checked(ctx.inputs['in']),ensure_ascii=False,indent=2)})\n        if ctx.node['typeId']=='p08.json-text':")
    s=s.replace('    v=v or SchemaAdapter','    catalog=profile.CATALOG\n    old=catalog.parent/\'catalog-0.1.2.json\'\n    if w[\'catalogLock\'][\'sha256\']==hashlib.sha256(old.read_bytes()).hexdigest():catalog=old\n    v=v or SchemaAdapter').replace('profile.CATALOG,v,registry or Registry','catalog,v,registry or Registry')
    s=s.replace("'model_adapter.py','local_models.py'","'model_adapter.py','task_extract.py','local_models.py'")
    hook="""        if op=='load' and b.get('action')=='task-template':
            p007.p006.exact(b,('action','provider'))
            if b['provider'] not in ('Ollama','LM Studio'):raise ContractError('LOCAL_MODEL_UNAVAILABLE')
            return task_extract.document(b['provider'])
        if op=='load' and b.get('action') in ('task-save','task-open'):
            saving=b['action']=='task-save'
            p007.p006.exact(b,('action','name','runId') if saving else ('action','name'))
            if not isinstance(b['name'],str) or not re.fullmatch('[A-Za-z0-9_-]{1,48}',b['name']):raise ContractError('DOCUMENT_NAME_DENIED')
            directory=self.workspace/'results';path=directory/(b['name']+'.json')
            if directory.is_symlink() or path.is_symlink() or path.resolve().parent.parent!=self.workspace.resolve():raise ContractError('RESULT_PATH_DENIED')
            if not saving:
                if not path.is_file():raise ContractError('RESULT_NOT_FOUND')
                return task_extract.checked(path.read_text(encoding='utf-8').strip())
            self.require_run();snap=self.s.runtime.snapshot
            if snap['runId']!=b['runId'] or snap['state']!='succeeded' or not any(a['key']=='main/output' and a['status']=='consumed' for a in snap['approvals'].values()):raise ContractError('RESULT_REVIEW_REQUIRED')
            data=task_extract.checked(snap['scopes']['main']['result'])
            directory.mkdir(exist_ok=True)
            from tempfile import NamedTemporaryFile
            with NamedTemporaryFile(mode='w',encoding='utf-8',dir=directory,delete=False) as tmp:
                json.dump(data,tmp,ensure_ascii=False,indent=2)
            try:os.link(tmp.name,path)
            except FileExistsError:raise ContractError('RESULT_NAME_EXISTS')
            finally:Path(tmp.name).unlink(missing_ok=True)
            return {'saved':path.name}
"""
    f.write_text(s.replace("        if op=='health':",hook+"        if op=='health':"),encoding='utf8')
