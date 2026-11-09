"""Read-only native Codex skills discovery. No threads, turns, model calls or config writes."""
from pathlib import Path
import json,queue,subprocess,threading,sys
HERE=Path(__file__).resolve().parent
CODEX=Path(r'C:\Users\Administrator\AppData\Local\OpenAI\Codex\bin\e78bad9887fa50cf\codex.exe')
def probe(label):
    out=HERE/'evidence';out.mkdir(exist_ok=True)
    with (out/(label+'-discovery-stderr.log')).open('wb') as log:
        p=subprocess.Popen([str(CODEX),'app-server','--stdio'],cwd=r'D:\AIOrchestrationStudio',stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=log,text=True,encoding='utf-8',creationflags=subprocess.CREATE_NO_WINDOW)
        q=queue.Queue()
        def reader():
            for line in p.stdout:
                try:q.put(json.loads(line))
                except ValueError:pass
            q.put(None)
        threading.Thread(target=reader,daemon=True).start()
        def request(id,method,params):
            p.stdin.write(json.dumps({'id':id,'method':method,'params':params})+'\n');p.stdin.flush()
            for _ in range(100):
                v=q.get(timeout=35)
                if v is None:raise RuntimeError('app-server exited')
                if v.get('id')==id:return v
            raise RuntimeError('No correlated response')
        try:
            init=request(1,'initialize',{'clientInfo':{'name':'aos_skill_inventory','version':'0.1.0'},'capabilities':{'experimentalApi':True}})
            if 'error' in init:raise RuntimeError(init['error'])
            p.stdin.write('{"method":"initialized"}\n');p.stdin.flush()
            reply=request(2,'skills/list',{'cwds':[r'D:\AIOrchestrationStudio',str(HERE)],'forceReload':True})
            (out/(label+'-skills.json')).write_text(json.dumps(reply,ensure_ascii=False,indent=2),encoding='utf-8')
            print(json.dumps(reply,ensure_ascii=False)[:1000])
        finally:
            p.stdin.close()
            try:p.wait(timeout=5)
            except subprocess.TimeoutExpired:p.kill();p.wait()
            p.stdout.close()
if __name__=='__main__':probe(sys.argv[1])
