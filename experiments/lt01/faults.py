"""Launch isolated C1 processes and check durable state before/after restart."""
import json
import subprocess
import sys
import time
from score import ROOT,authoritative,records
def campaign():
    results={}
    batch=str(time.time_ns())
    for mode,expected,key in [('timeout','unknown','model'),('mcp-stop','failed','read'),('bad-port','failed','normalize'),
                              ('crash','unknown','join'),('lost','unknown','model')]:
        label='fault-'+mode+'-'+batch;d=ROOT/'runs'/label
        command=[sys.executable,'-B','-X','utf8',str(ROOT/'flow.py'),label,'--size','200','--fault',mode]
        first=subprocess.run(command,capture_output=True,encoding='utf-8',timeout=60)
        (d/'first.log').write_text(first.stdout+first.stderr,'utf-8')
        before=authoritative(d);wire=records(d)
        second=subprocess.run([*command,'--resume'],capture_output=True,encoding='utf-8',timeout=60)
        (d/'restart.log').write_text(second.stdout+second.stderr,'utf-8')
        after=authoritative(d);n=after['nodes']['main/'+key]
        same=all(old['attempts']==after['nodes'][k]['attempts'] for k,old in before['nodes'].items() if old['state']=='succeeded')
        unchanged=after['runId']==before['runId'] and records(d)==wire and all(len(v['attempts'])<=1 for v in after['nodes'].values())
        unsafe=not unchanged or (d/'results').exists() or bool(after['nodes']['main/output']['attempts'])
        expected_code={'timeout':'LOCAL_SERVICE_UNAVAILABLE_OR_RESPONSE_LOST','lost':'LOCAL_SERVICE_UNAVAILABLE_OR_RESPONSE_LOST',
                       'crash':'INTERRUPTED_IN_FLIGHT','bad-port':'PORT_VALUE_INVALID','mcp-stop':'MCP_READ_FAILED'}[mode]
        verified=(first.returncode==(74 if mode=='crash' else 0) and second.returncode==0 and n['state']==expected
                  and after['state']==expected and n['error']['code']==expected_code and same and not unsafe)
        results[mode]=dict(label=label,verified=verified,unsafe=unsafe,firstState=before['state'],finalState=after['state'],
                           code=n.get('error'),finishedNodesPreserved=same,dispatchCount=sum(i['kind']=='generate' for i in wire),
                           serviceResponses=sum(i['kind']=='received' for i in wire),firstExit=first.returncode,restartExit=second.returncode)
        (ROOT/'challenges.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),'utf-8')
        print(mode,results[mode],flush=True)
    return all(v['verified'] for v in results.values())
if __name__=='__main__':sys.exit(0 if campaign() else 1)

