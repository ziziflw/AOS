// Run only against a private copy of the packaged runtime and synthetic documents.
const fs=require('node:fs'),path=require('node:path'),cp=require('node:child_process'),assert=require('node:assert/strict')
const {chromium}=require(process.env.AOS_PLAYWRIGHT||'C:/Users/Administrator/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright')
const project=path.resolve(__dirname,'../..'),root=path.join(__dirname,'.runtime/experiments/p0-08')
const exe=path.join(project,'apps/aos-workbench/.desktop-preview/AOS-Integrated.exe')
const phase=process.argv[2]||'edit',dir=path.join(__dirname,'evidence',phase+'-'+Date.now()),ses=path.join(root,'evidence',phase==='replay'?path.basename(process.argv[3]):path.basename(dir))
const sleep=ms=>new Promise(r=>setTimeout(r,ms))
const json=f=>JSON.parse(fs.readFileSync(f,'utf8').replace(/^\uFEFF/,''))
const write=(f,x)=>fs.writeFileSync(path.join(dir,f),JSON.stringify(x,null,2))
const checks=[];let browser,p,proc
async function boot(){
 if(await fetch('http://127.0.0.1:9238/json/version').then(()=>true,()=>false))throw Error('debug port already occupied')
 proc=cp.spawn(exe,[root,ses,'test'],{stdio:'ignore'})
 for(let i=0;i<80&&!browser;i++){try{browser=await chromium.connectOverCDP('http://127.0.0.1:9238')}catch{await sleep(160)}}
 p=browser.contexts()[0].pages()[0];p.setDefaultTimeout(7000)
 await p.getByTestId('run').waitFor()
 await p.waitForFunction(()=>document.querySelectorAll('[data-node-id]').length>0,{}, {timeout:20000})
}
async function close(){
 if(p)await p.evaluate(()=>window.__TAURI__.core.invoke('window_report',{report:{close:true}})).catch(()=>{})
 if(browser)await browser.close();browser=null;p=null
 if(proc){if(proc.exitCode===null)await Promise.race([new Promise(r=>proc.once('exit',r)),sleep(2500)]);proc.unref();proc=null}
}
const btn=n=>p.getByRole('button',{name:n,exact:true}),lab=n=>p.getByLabel(n,{exact:true})
const ipc=async(op,body={})=>p.evaluate(async({op,body})=>{const reply=await window.__TAURI__.core.invoke('host_request',{request:{v:'aos-local/0.1',kind:'request',id:crypto.randomUUID(),op,body}});return reply},{op,body})
async function sidebar(n){const control=p.locator('.rail').getByRole('button',{name:n,exact:true});if(await control.getAttribute('aria-pressed')!=='true')await control.click()}
async function tpl(code){await sidebar('文件');await p.locator('[data-example="'+code+'"]').click()}
async function add(t){await sidebar('组件');const h=(await ipc('health')).result;await lab('搜索组件').fill(h.labels[t]);await p.locator('[data-type="'+t+'"]').click()}
async function select(id){await p.locator('[data-node-id="'+id+'"]').dblclick();await p.locator('.editor-form').waitFor()}
async function join(a,b){await select(a);await p.locator('[data-port="out"]').click();await select(b);await p.locator('[data-port="in"]').click()}
async function waitState(state){
 await p.waitForFunction(s=>document.querySelector('[data-testid=state]')?.textContent.includes(s),state,{timeout:25000})
 return (await ipc('status')).result
}
function db(){const key=json(path.join(ses,'latest.json')).key;return path.join(ses,'runs',key)}
async function evidence(tag){
 const s=(await ipc('status')).result
 const code="import sqlite3,json,sys;print(sqlite3.connect(sys.argv[1]).execute('select state from snapshot where id=1').fetchone()[0])"
 const disk=JSON.parse(cp.execFileSync(path.join(root,'.venv/Scripts/python.exe'),['-X','utf8','-c',code,path.join(db(),'run.sqlite')],{encoding:'utf8'}))
 assert.deepEqual(s,disk);if(s.state==='succeeded')assert.equal(await p.getByTestId('output').innerText(),s.scopes.main.result)
 write(tag+'.json',{run:s.runId,state:s.state,result:s.scopes.main.result,usage:s.usage,nodes:Object.fromEntries(Object.entries(s.nodes).map(([k,n])=>[k,{state:n.state,count:n.attempts.length,error:n.error,usage:n.modelUsage,output:n.outputs?.out?.payload}]))})
 checks.push(tag+': UI/SQLite '+s.state);await p.screenshot({path:path.join(dir,tag+'.png')});return s
}
async function edit(){
 await sidebar('文件');await btn('新建工作流').click();await btn('校验').click();await p.locator('h1').click();await p.keyboard.press('Control+a');await p.keyboard.press('Delete');await p.waitForFunction(()=>document.querySelectorAll('[data-node-id]').length===0);await add('synth.source');await add('p08.lmstudio.text');await add('synth.output')
 const [a,b,c]=await p.locator('[data-node-id]').evaluateAll(ns=>ns.map(n=>n.dataset.nodeId))
 await select(a);await lab('value').fill('只回答工单号：测试工单 AX-17。');await lab('value').press('Tab')
 await select(b);await p.locator('[data-port=out]').click();await p.locator('[data-port=in]').click();await p.getByText('不能连接到自身',{exact:true}).waitFor();checks.push('UI rejected self-edge');await join(a,b);await join(b,c)
 await sidebar('文件');const name='p011-'+Date.now();await lab('文档名称').fill(name);await btn('保存工作流').click();await btn(name).waitFor()
 const d=(await ipc('load',{action:'open',name})).result
 assert.equal(d.workflow.graph.edges.length,2);assert.equal(d.workflow.graph.nodes[0].config.value,'只回答工单号：测试工单 AX-17。')
 await btn('新建工作流').click();await sidebar('文件');await btn(name).click();await btn('保存工作流').click()
 assert.deepEqual((await ipc('load',{action:'open',name})).result,d);checks.push('create/add/connect/edit/save/open roundtrip')
 const bad=structuredClone(d.workflow);bad.graph.edges[0].from.port='absent';const invalid=await ipc('load',{action:'validate',workflow:bad});assert.equal(invalid.ok,false);checks.push(invalid.error.code)
 await sidebar('模型');await btn('测试连接').click();await lab('模型 ID').selectOption('google/gemma-4-e4b');await btn('保存连接').click();await p.getByText('已保存，下次运行时生效').waitFor()
 await p.getByTestId('run').click();await waitState('完成');const s=await evidence('gemma-text');assert.equal(s.nodes['main/'+b].attempts.length,1)
}
async function templates(){
 for(const code of (phase.startsWith('WF-')?[phase]:['WF-02','WF-03','WF-01'])){
  await tpl(code);await p.getByTestId('run').click()
  if(code!=='WF-02'){
   const old=await waitState('等待审批');const key=code==='WF-03'?'main/tool':'main/output';assert.equal(old.nodes[key].attempts.length,0)
   if(code==='WF-03'){
    const positions=()=>p.locator('[data-node-id]').evaluateAll(ns=>Object.fromEntries(ns.map(n=>[n.dataset.nodeId,n.closest('.vue-flow__node').style.transform])))
    const expectedPositions=await positions();assert.ok(new Set(Object.values(expectedPositions)).size>=3)
    const broken=await ipc('approve',{approvalId:old.nodes[key].approvalId,fingerprint:'obsolete',decision:true});assert.equal(broken.ok,false)
    await close()
    for(let i=0;i<60;i++){if(!await fetch('http://127.0.0.1:9238/json/version').then(()=>true,()=>false))break;await sleep(100)}
    await boot();await p.locator('[data-node-id=tool] .node-state').filter({hasText:'等待审批'}).waitFor();await sidebar('运行');const now=await waitState('等待审批');assert.equal(now.runId,old.runId);assert.deepEqual(now.nodes,old.nodes);assert.deepEqual(await positions(),expectedPositions);write('recovered-layout.json',expectedPositions);checks.push('node coordinates restored exactly at approval')
   }
   await btn('批准本次操作').click()
  }
  await waitState('完成');const s=await evidence(code)
  if(code==='WF-01')assert.equal(JSON.parse(s.scopes.main.result).tasks.length,2)
  else assert.equal(s.nodes['main/tool'].attempts.length,1)
 }
}
async function environmentCheck(){
 const settings=path.join(root,'workspace/local-models.json'),previous=fs.readFileSync(settings)
 try{
  fs.writeFileSync(settings,JSON.stringify({'LM Studio':{model:'p011-missing-fixture',url:'http://127.0.0.1:1234/v1'}}))
  await tpl('WF-01');await p.getByRole('alert').filter({hasText:'LOCAL_MODEL_UNAVAILABLE'}).waitFor()
  assert.equal(await p.locator('[data-node-id]').count(),5)
  assert.equal(fs.existsSync(path.join(ses,'latest.json')),false);checks.push('template loaded with missing model diagnosed; no generation')
 }finally{fs.writeFileSync(settings,previous)}
}
async function portability(){
 await tpl('WF-02')
 await select('text');await p.locator('[data-port=out]').click();await select('tool');await p.locator('[data-port=args]').click()
 await p.getByText(/类型不兼容/).first().waitFor();checks.push('UI rejects Text -> MCPArgs')
 const folder=path.join(project,'examples/workflows')
 const d={workflow:json(path.join(folder,'WF-02.workflow.json')),layout:json(path.join(folder,'WF-02.layout.json'))}
 d.workflow.graph.nodes[0].typeId='future.source';d.workflow.graph.nodes[0].typeVersion='9.0.0'
 await sidebar('文件')
 await p.locator('input[type=file]').setInputFiles({name:'unknown.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(d))})
 await p.getByText('未知节点 · future.source').waitFor()
 const name='future-'+Date.now();await lab('文档名称').fill(name);await btn('保存工作流').click();await btn(name).waitFor()
 const saved=(await ipc('load',{action:'open',name})).result
 assert.deepEqual(saved,d);await btn('校验').click();await p.getByRole('alert').filter({hasText:'NODE_UNRESOLVED'}).waitFor()
 checks.push('unknown node, version, config, layout and edges preserved; execution refused')
 await tpl('WF-02');await p.getByTestId('run').click();await waitState('完成');await evidence('WF-02')
 await p.locator('summary').filter({hasText:'事件'}).click()
 const snapshot=(await ipc('status')).result
 await p.waitForFunction(seq=>[...document.querySelectorAll('.run-view details div')].some(v=>v.textContent.startsWith(seq+' ·')),snapshot.seq)
 const seqs=await p.locator('.run-view details div').evaluateAll(xs=>xs.map(x=>Number(x.textContent.split(' · ')[0])))
 assert.equal(seqs.length,new Set(seqs).size);assert.equal(seqs.length,snapshot.seq);checks.push('all run event sequence numbers displayed once')
}
async function faults(){
 await tpl('WF-03');await p.getByTestId('run').click();const before=await waitState('等待审批')
 await select('text');await lab('value').fill('后续修订');await lab('value').press('Tab')
 const pinned=(await ipc('load',{action:'run-definition'})).result;assert.notEqual(pinned.graph.nodes[0].config.value,'后续修订')
 await sidebar('运行');await btn('取消运行').click();await waitState('已取消');const cancelled=await evidence('cancel');assert.equal(cancelled.runId,before.runId);assert.equal(cancelled.nodes['main/tool'].attempts.length,0)
 const settings=path.join(root,'workspace/local-models.json'),orig=fs.readFileSync(settings)
 try{
  fs.writeFileSync(settings,JSON.stringify({'LM Studio':{url:'http://127.0.0.1:1/v1',model:'google/gemma-4-e4b'}}))
  await tpl('WF-01');await p.getByTestId('run').click()
  await p.waitForFunction(()=>document.querySelector('.run-view')?.innerText.includes('LOCAL_SERVICE_UNAVAILABLE'),{},{timeout:15000});const lost=await (async()=>{await waitState('失败');return evidence('disconnect')})();assert.equal(lost.state,'failed');assert.equal(lost.nodes['main/model'].error.code,'LOCAL_SERVICE_UNAVAILABLE_BEFORE_REQUEST')
 }finally{fs.writeFileSync(settings,orig)}
}
(async()=>{fs.mkdirSync(dir,{recursive:true});let failure
 try{await boot();if(phase==='environment')await environmentCheck();else if(phase==='replay'){await p.locator('.node-state').first().waitFor();await sidebar('运行');await waitState('完成');await evidence('restored');assert.ok(await p.locator('.canvas-host').evaluate(e=>e.clientHeight>window.innerHeight*.8));checks.push('native full-height canvas; restored without new generation')}else if(phase==='portability')await portability();else if(phase==='edit')await edit();else if(phase==='templates'||phase.startsWith('WF-'))await templates();else await faults()}
 catch(e){failure=String(e);if(p){write('diagnostic.json',{text:await p.locator('body').innerText()});await p.screenshot({path:path.join(dir,'failure.png')})}}
 finally{await close();write('checks.json',{checks,failure});console.log(dir,checks,failure||'');process.exitCode=failure?1:0}
})()

