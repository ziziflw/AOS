"""Same Gemma request replayed once through the SDK; no oracle in the prompt."""
import argparse
import json
import time
import openai
import httpx2
from flow import ROOT,ID,read,write,fetch
from audit import adjudicate

def main(label,size):
    directory=ROOT/'runs'/label
    out=directory/'direct.json'
    if out.exists():raise FileExistsError(out)
    records=[json.loads(v) for v in (directory/'requests.jsonl').read_text('utf-8').splitlines()]
    body=next(v['body'] for v in records if v['kind']=='generate')
    assert body['model']==ID and body['max_tokens']==384 and len(body['messages'])==1
    facts=fetch(directory/'blobs',read(directory/'snapshot.json')['nodes']['main/join']['outputs']['out']['payload'])
    start=time.perf_counter()
    with openai.OpenAI(base_url='http://127.0.0.1:1234/v1',api_key='local-no-auth',timeout=20,max_retries=0,
                       http_client=httpx2.Client(trust_env=False,follow_redirects=False)) as client:
        result=client.chat.completions.create(**body,extra_headers={'Authorization':openai.omit})
    elapsed=time.perf_counter()-start
    reply=result.choices[0];raw=reply.message.content
    record=dict(model=result.model,seconds=elapsed,usage=result.usage.model_dump(),finish=reply.finish_reason,raw=raw,body=body)
    try:
        if reply.finish_reason!='stop':raise ValueError('INCOMPLETE')
        items=adjudicate(raw,facts['tickets'])
        expected=read(ROOT/'oracle'/(size+'.json'))
        truth={'T'+str(int(k[1:])):v['review'] for k,v in expected.items() if v['review']}
        record['ticketCategoryScore']=sum(truth[v['ticket']]==v['category'] for v in items)/len(truth)
        record['advice']=items
    except ValueError as e:record['error']=str(e)
    finally:write(out,record)
    print(label,elapsed,record.get('ticketCategoryScore'),result.usage.total_tokens)

if __name__=='__main__':
    import re
    p=argparse.ArgumentParser();p.add_argument('label');p.add_argument('size',choices=['30','200']);a=p.parse_args()
    if not re.fullmatch('[A-Za-z0-9_-]{1,48}',a.label):p.error('invalid label')
    main(a.label,a.size)

