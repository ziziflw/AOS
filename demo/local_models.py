"""Explicit loopback connections. User settings live next to the managed workspace."""
import json, os
from pathlib import Path
from urllib.parse import urlsplit
import openai, httpx2
CONFIG=Path(__file__).resolve().parent/'workspace/local-models.json'
PRESETS={'Ollama':'http://127.0.0.1:11434/v1','LM Studio':'http://127.0.0.1:1234/v1'}
def checked(url):
    p=urlsplit(url)
    if p.scheme!='http' or p.hostname!='127.0.0.1' or not p.port or p.username or p.password or p.path.rstrip('/')!='/v1' or p.query or p.fragment:
        raise ValueError('仅允许 http://127.0.0.1:端口/v1')
    return f'http://127.0.0.1:{p.port}/v1'
def read():
    return json.loads(CONFIG.read_text('utf-8')) if CONFIG.is_file() else {}
def models(url):
    with openai.OpenAI(base_url=checked(url),api_key='local-no-auth',max_retries=0,timeout=3,http_client=httpx2.Client(trust_env=False,follow_redirects=False)) as client:
        return [m.id for m in client.models.list(extra_headers={'Authorization':openai.omit}).data]
async def invoke(ctx,binding,adapter):
    from model_adapter import ModelResult
    from common import OutcomeError
    if not binding:raise OutcomeError('LOCAL_CONNECTION_NOT_CONFIGURED')
    try:
        async with openai.AsyncOpenAI(base_url=checked(binding['url']),api_key='local-no-auth',max_retries=0,timeout=20,http_client=httpx2.AsyncClient(trust_env=False,follow_redirects=False)) as client:
            try:
                available=await client.models.list(extra_headers={'Authorization':openai.omit})
            except openai.APIConnectionError:
                # Discovery is read-only. No generation has been dispatched yet.
                adapter.observations[ctx.attempt_id]={'usage':{'inputTokens':0,'outputTokens':0},'responseReceived':False}
                raise OutcomeError('LOCAL_SERVICE_UNAVAILABLE_BEFORE_REQUEST') from None
            if binding['model'] not in [m.id for m in available.data]:raise OutcomeError('LOCAL_MODEL_UNAVAILABLE')
            if ctx.cancel.is_set():raise OutcomeError('LOCAL_CANCELLED_BEFORE_REQUEST')
            options = {}
            if ctx.node['typeId'] == 'p08.lmstudio.text' and binding['model'] == 'google/gemma-4-e4b':
                # On the verified short-text profile, reasoning can consume the entire output limit.
                options['reasoning_effort'] = 'none'
            r=await client.chat.completions.create(model=binding['model'],messages=[{'role':'user','content':ctx.inputs['in']}],max_tokens=ctx.node['config']['maxOutputTokens'],stream=False,extra_headers={'Authorization':openai.omit},**options)
            usage={'inputTokens':r.usage.prompt_tokens,'outputTokens':r.usage.completion_tokens} if r.usage else None
            if usage and any(type(n)!=int or n<0 for n in usage.values()):raise OutcomeError('LOCAL_USAGE_INVALID',side_effect='unknown')
            adapter.observations[ctx.attempt_id]={'usage':usage,'responseReceived':True}
            choice = next(iter(r.choices), None)
            if not choice or not (choice.message.content or '').strip():
                code = 'LOCAL_OUTPUT_LIMIT_NO_TEXT' if choice and choice.finish_reason == 'length' else 'LOCAL_EMPTY_RESPONSE'
                raise OutcomeError(code)
            if choice.finish_reason == 'length':
                # A partial completion must not be published on the validated text port.
                raise OutcomeError('LOCAL_OUTPUT_TRUNCATED', side_effect='confirmed')
            return ModelResult({'out':choice.message.content},usage_tokens=sum(usage.values()) if usage else 0,model_usage=usage)
    except openai.APIStatusError as e:raise OutcomeError('LOCAL_HTTP_'+str(e.status_code)) from None
    except openai.APIConnectionError:raise OutcomeError('LOCAL_SERVICE_UNAVAILABLE_OR_RESPONSE_LOST',side_effect='unknown') from None
def configure():
    import sys
    rt=Path(sys.executable).parent.parent
    os.environ['TCL_LIBRARY']=str(rt/'tcl/tcl8.6');os.environ['TK_LIBRARY']=str(rt/'tcl/tk8.6')
    import tkinter as tk
    from tkinter import ttk
    w=tk.Tk();w.title('AOS · 本地模型连接');w.geometry('440x260')
    kind=tk.StringVar(value='Ollama');url=tk.StringVar();model=tk.StringVar();msg=tk.StringVar()
    def reset(*_):
        current=read().get(kind.get(),{});url.set(current.get('url',PRESETS[kind.get()]));model.set(current.get('model',''))
    def test():
        try:
            ids=models(url.get());box.configure(values=ids);model.set(ids[0] if ids else '');msg.set('连接成功' if ids else '服务在线，模型列表为空')
        except Exception:msg.set('连接失败，请检查服务状态与地址')
    def save():
        try:
            if model.get() not in models(url.get()):raise ValueError()
            data=read();data[kind.get()]={'url':checked(url.get()),'model':model.get()}
            CONFIG.parent.mkdir(exist_ok=True);temp=CONFIG.with_suffix(f'.{os.getpid()}.tmp');temp.write_text(json.dumps(data),'utf-8');temp.replace(CONFIG);msg.set('已保存，可在工作台选择此连接')
        except Exception:msg.set('请先连接服务并选择有效模型')
    for label,widget in [('服务',ttk.Combobox(w,textvariable=kind,values=list(PRESETS),state='readonly')),('服务地址',ttk.Entry(w,textvariable=url,width=45)),('模型',ttk.Combobox(w,textvariable=model,state='readonly'))]:
        ttk.Label(w,text=label).pack();widget.pack()
    box=widget;ttk.Button(w,text='测试连接并获取模型',command=test).pack();ttk.Button(w,text='保存连接',command=save).pack();ttk.Label(w,textvariable=msg).pack();kind.trace_add('write',reset);reset();w.mainloop()
if __name__=='__main__':configure()
