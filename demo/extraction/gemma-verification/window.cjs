const fs = require('node:fs'), path = require('node:path'), cp = require('node:child_process'), assert = require('node:assert/strict');
const {chromium} = require('C:/Users/Administrator/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const out = __dirname, project = path.resolve(out, '../../..');
const root = path.join(process.env.LOCALAPPDATA, 'AOS-Demo/v0.1.3/experiments/p0-08');
const id = 'google/gemma-4-e4b', prompt = '请简要说明软件开发中工作流编排的作用，限制在100字以内。';
const meeting = '明天下午三点开项目会议，张三负责准备演示材料，李四负责整理测试记录。';
const write = (name, data) => fs.writeFileSync(path.join(out,name),JSON.stringify(data,null,2));
(async()=>{
 const proc = cp.spawn(path.join(project,'demo/studio/workbench.exe'),[root,path.join(root,'evidence',process.argv[2] || 'gemma-'+Date.now()),'test'],{stdio:'ignore'});
 let browser,page;
 try {
  for(let i=0;i<80 && !browser;i++){try{browser=await chromium.connectOverCDP('http://127.0.0.1:9238')}catch{await new Promise(r=>setTimeout(r,180))}}
  page=browser.contexts()[0].pages()[0]; page.setDefaultTimeout(10000);
  const button=name=>page.getByRole('button',{name,exact:true}), label=name=>page.getByLabel(name,{exact:true});
  const ipc=(op,body={})=>page.evaluate(async({op,body})=>(await window.__TAURI__.core.invoke('host_request',{request:{v:'aos-local/0.1',kind:'request',id:crypto.randomUUID(),op,body}})).result,{op,body});
  if(process.argv[2]){
   if(process.argv[3]){
    await button('打开').click();await button(process.argv[3]).click();
    await page.waitForFunction(()=>document.querySelectorAll('.graph-node').length===3);
    await page.getByTestId('run').click();
    await page.waitForFunction(()=>document.querySelector('[data-testid=output]')?.textContent.includes('工作流') && document.querySelector('[data-testid=run-state]').textContent.includes('完成'));
    const s=await ipc('status');assert.equal(s.workflowId,'gemma-text');assert.notEqual(s.runId,require('./text.json').snapshot.runId);
    write('text-reopened.json',{snapshot:s});await page.screenshot({path:path.join(out,'text-reopened.png')});return;
   }
   await button('批准本次操作').waitFor();
   const before=await ipc('status');assert.equal(before.runId,require('./tasks.json').snapshot.runId);
   await button('批准本次操作').click();
   await page.waitForFunction(()=>document.querySelector('[data-testid=run-state]').textContent.includes('完成'));
   const after=await ipc('status');assert.equal(after.nodes['main/model'].attempts.length,1);
   assert.deepEqual(JSON.parse(await page.getByTestId('output').innerText()),after.scopes.main.result);
   write('tasks-approved.json',{snapshot:after});await page.screenshot({path:path.join(out,'tasks.png')});
   return;
  }
  await button('使用离线示例').click();
  await page.locator('[aria-label="连接"]:visible').locator('..').click();
  await label('本地服务').selectOption('LM Studio');
  await page.waitForFunction(()=>document.querySelector('[aria-label="回环地址"]').value==='http://127.0.0.1:1234/v1');
  await button('测试连接并获取模型').click(); await label('发现的模型').selectOption(id);
  await button('保存连接').click(); await page.getByText('已保存，下次运行时生效',{exact:true}).waitFor();
  assert.equal((await ipc('load',{action:'local-settings'}))['LM Studio'].model,id);
  await page.screenshot({path:path.join(out,'connection.png')});
  const doc=await ipc('load',{action:'task-template',provider:'LM Studio'});
  const graph=doc.workflow.graph;
  graph.nodes=graph.nodes.filter(n=>['text','model','output'].includes(n.id));
  graph.nodes[0].config.value=prompt; graph.nodes[1].config.maxOutputTokens=128;
  graph.nodes[2].policy.approval='policy';
  graph.edges=[graph.edges[0],graph.edges[2]];graph.edges[0].to.node='model';graph.edges[1].to.node='output';
  doc.workflow.title='Gemma · 工作流编排';doc.workflow.workflowId='gemma-text';
  doc.layout.positions={text:{x:0,y:60},model:{x:260,y:60},output:{x:520,y:60}};
  write('gemma-text.document.json',doc);
  await page.locator('input[type=file]').setInputFiles(path.join(out,'gemma-text.document.json'));
  await page.waitForFunction(()=>document.querySelectorAll('.graph-node').length===3);
  await button('打开').click();const name='gemma-text-'+Date.now().toString().slice(-8);
  await label('文档名称').fill(name);await button('保存').click();await button(name).waitFor();await button(name).click();
  await page.getByText('已重新加载 · '+name,{exact:true}).first().waitFor({timeout:2000}).catch(()=>{});
  const persisted=await ipc('load',{action:'open',name});assert.equal(persisted.workflow.graph.nodes.find(n=>n.id==='model').config.maxOutputTokens,128);
  async function run(tag,review=false){
   const before=(await ipc('status'))?.runId;
   const start=performance.now();await page.getByTestId('run').click();
   let s;
   for(let k=0;k<160;k++){s=await ipc('status');if(s?.runId && s.runId!==before && ['waiting-approval','succeeded','failed','unknown','cancelled'].includes(s.state))break;await page.waitForTimeout(150)}
   write(tag+'.json',{snapshot:s,clickToObservedMs:performance.now()-start});
   if(review && s.state==='waiting-approval'){
    const parsed=JSON.parse(s.nodes['main/model'].outputs.out.payload);assert.ok(Array.isArray(parsed.tasks));
    await button('批准本次操作').click();await page.waitForFunction(()=>document.querySelector('[data-testid=run-state]').textContent.includes('完成'));s=await ipc('status');
    write(tag+'-approved.json',{snapshot:s,clickToObservedMs:performance.now()-start});
   }
   assert.equal(s.state,'succeeded',JSON.stringify(s.nodes['main/model'].error));await page.getByTestId('output').waitFor();
   await page.waitForFunction(()=>document.querySelector('[data-testid=run-state]').textContent.includes('完成'));
   const uiText=await page.getByTestId('output').innerText();assert.deepEqual(JSON.parse(uiText),s.scopes.main.result);
   await page.screenshot({path:path.join(out,tag+'.png')});console.log(tag,s.runId,s.scopes.main.result);
  }
  await run('text');
  await label('提取模型').selectOption('LM Studio');await button('打开任务提取工作流').click();
  await page.locator('[data-node-id=text] header').click();await label('value').fill(meeting);await label('value').press('Tab');
  await run('tasks',true);
 }catch(e){if(page){console.error((await page.locator('body').innerText()).slice(-3500));await page.screenshot({path:path.join(out,'diagnostic.png')})}throw e}
 finally{if(page)await page.evaluate(()=>window.__TAURI__.core.invoke('window_report',{report:{close:true}})).catch(()=>{});if(browser)await browser.close();proc.unref()}
})().catch(e=>{console.error(e);process.exitCode=1});
