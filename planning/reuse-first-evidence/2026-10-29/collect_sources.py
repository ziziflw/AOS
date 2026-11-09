"""Read public metadata/license files only. Never install/import upstream packages."""
from pathlib import Path
import concurrent.futures,hashlib,json,urllib.request,datetime
HERE=Path(__file__).resolve().parent
REPOS=['bcakmakoglu/vue-flow','modelcontextprotocol/python-sdk','a2aproject/a2a-python','BerriAI/litellm','vercel/ai','openai/openai-python','anthropics/anthropic-sdk-python','langchain-ai/langgraph','open-telemetry/opentelemetry-python','Comfy-Org/ComfyUI','eclipsesource/jsonforms','jaraco/keyring','temporalio/sdk-python']
PACKAGES=['litellm','litellm-core','openai','anthropic','langgraph','langgraph-checkpoint-sqlite','opentelemetry-api','opentelemetry-sdk','keyring']
def get(url):
    with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'AOS-read-only-reuse-assessment','Accept':'application/vnd.github+json' if 'api.github.com' in url else '*/*'}),timeout=25) as r:return r.read()
def repo(name):
    out={'requestedRepository':name,'errors':[]}
    try:
        meta=json.loads(get('https://api.github.com/repos/'+name))
        out.update(repository=meta['full_name'],url=meta['html_url'],archived=meta['archived'],pushedAt=meta['pushed_at'],declaredLicense=meta.get('license'))
        commit=json.loads(get('https://api.github.com/repos/'+meta['full_name']+'/commits/HEAD'))
        out.update(commit=commit['sha'],commitDate=commit['commit']['committer']['date'])
        for file in ['LICENSE','LICENSE.md','LICENSE.txt','LICENSE-MIT']:
            url='https://raw.githubusercontent.com/'+meta['full_name']+'/'+commit['sha']+'/'+file
            try:
                body=get(url);dest=HERE/'upstream-licenses'/name.replace('/','__')/file;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(body)
                out.update(licensePath=str(dest.relative_to(HERE)),licenseURL=url,licenseSHA256=hashlib.sha256(body).hexdigest());break
            except Exception as e:
                if '404' not in str(e):out['errors'].append(file+': '+str(e))
        if 'licensePath' not in out:out['errors'].append('License file not obtained')
    except Exception as e:out['errors'].append(str(e))
    return out
def package(name):
    try:
        data=json.loads(get('https://pypi.org/pypi/'+name+'/json'));i=data['info']
        return {'name':name,'version':i['version'],'requiresPython':i.get('requires_python'),'requiresDist':i.get('requires_dist'),'license':i.get('license'),'licenseExpression':i.get('license_expression'),'projectURLs':i.get('project_urls'),'artifacts':[{'filename':x['filename'],'sha256':x['digests']['sha256'],'yanked':x['yanked'],'uploadTime':x['upload_time_iso_8601'],'bytes':x['size']} for x in data['urls']],'status':'metadata only; not installed, not security approved'}
    except Exception as e:return {'name':name,'error':str(e)}
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
    repos=list(pool.map(repo,REPOS));packages=list(pool.map(package,PACKAGES))
out={'retrievedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'reviewDateAsiaShanghai':'2026-10-29','repositories':repos,'pypiMetadata':packages,'scope':'public metadata/licenses only; no dependency resolution, installation, import, provider call or upstream script execution'}
(HERE/'upstream-snapshot.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'repositories':[{'name':x.get('repository',x['requestedRepository']),'sha':x.get('commit'),'license':(x.get('declaredLicense')or{}).get('spdx_id'),'errors':x['errors']} for x in repos],'packages':[{'name':x['name'],'version':x.get('version'),'error':x.get('error')} for x in packages]},ensure_ascii=False))
