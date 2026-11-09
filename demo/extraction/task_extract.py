import json
from jsonschema import Draft202012Validator
from common import OutcomeError
TYPE='aos.validate-tasks'
SOURCE='周一例会：小林负责在周五前整理测试清单。小陈负责更新安装说明，未约定日期。'
INSTRUCTION='\n\n仅从上述记录提取明确分配的任务。仅返回 JSON 对象 {"tasks":[{"task":"动作","owner":"负责人或null","due":"原文日期或null"}]}。没有任务时返回空数组，不要解释或使用 Markdown。'
TEXT={'type':'string','minLength':1,'maxLength':1000}
OPTIONAL={'anyOf':[TEXT,{'type':'null'}]}
SCHEMA={'type':'object','additionalProperties':False,'required':['tasks'],'properties':{'tasks':{'type':'array','maxItems':100,'items':{'type':'object','additionalProperties':False,'required':['task','owner','due'],'properties':{'task':TEXT,'owner':OPTIONAL,'due':OPTIONAL}}}}}
def pairs(items):
    obj={}
    for key,val in items:
        if key in obj:raise ValueError('duplicate')
        obj[key]=val
    return obj
def checked(raw):
    try:data=json.loads(raw,object_pairs_hook=pairs)
    except (ValueError,TypeError,RecursionError):raise OutcomeError('TASK_JSON_INVALID') from None
    if not Draft202012Validator(SCHEMA).is_valid(data):raise OutcomeError('TASK_SCHEMA_INVALID')
    return data
def document(provider):
    from model_profile import sample,make_node,requirements,edge
    tid={'Ollama':'p08.ollama.text','LM Studio':'p08.lmstudio.text'}[provider]
    doc=sample(tid);w=doc['workflow'];source,model,out=w['graph']['nodes']
    source['config']['value']=SOURCE
    prompt=make_node('synth.step','prompt');prompt['config']['suffix']=INSTRUCTION
    model['config'].update(maxInputTokens=2048,maxOutputTokens=512,maxCallCostMinor=30)
    out['policy']['approval']='always'
    nodes=[source,prompt,model,make_node(TYPE,'validate'),out];ids=[n['id'] for n in nodes]
    w.update(workflowId='local-task-extraction',title='本地 AI 文本任务提取',environmentRequirements=requirements(nodes),graph={'nodes':nodes,'edges':[edge(a,b,index=i) for i,(a,b) in enumerate(zip(ids,ids[1:]))]})
    doc['layout']['positions']={id:{'x':i*260,'y':60} for i,id in enumerate(ids)}
    return doc
