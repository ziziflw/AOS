// Run E01 once through the v0.1.3 Tauri window, with two rapid run gestures.
const {chromium} = require('C:/Users/Administrator/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const fs = require('node:fs'), path = require('node:path'), cp = require('node:child_process'), assert = require('node:assert/strict');
const project = path.resolve(__dirname,'../..');
const root = path.join(process.env.LOCALAPPDATA,'AOS-Demo/v0.1.3/experiments/p0-08');
const session=path.join(root,'evidence','p010-window-'+Date.now());
const doc=require('../../demo/extraction/gemma-verification/gemma-text.document.json');
const test=JSON.parse(fs.readFileSync(path.join(__dirname,'cases.json'),'utf8').replace(/^\uFEFF/,'')).cases.find(c=>c.id==='E01');
doc.workflow.graph.nodes[0].config.value=test.input;
doc.workflow.graph.nodes[1].config.maxOutputTokens=test.maxTokens;
(async()=>{
 const proc=cp.spawn(path.join(project,'demo/studio/workbench.exe'),[root,session,'test'],{stdio:'ignore'});
 let browser,p;
 try {
  for(let i=0;i<100&&!browser;i++){try{browser=await chromium.connectOverCDP('http://127.0.0.1:9238')}catch{await new Promise(r=>setTimeout(r,150))}}
  p=browser.contexts()[0].pages()[0];
  await p.getByRole('button',{name:'使用离线示例',exact:true}).click({timeout:14000});
  await p.locator('input[type=file]').setInputFiles({name:'cutoff.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(doc))});
  await p.waitForFunction(()=>document.querySelectorAll('.graph-node').length===3);
  await p.getByTestId('run').click();await p.keyboard.press('Control+Enter');
  await p.waitForFunction(()=>document.querySelector('[data-testid=run-state]').textContent.includes('失败'));
  await p.getByRole('button',{name:/问题/}).first().click();
  await p.getByText(/model · LOCAL_OUTPUT_TRUNCATED/).first().waitFor();
  const reply=await p.evaluate(()=>window.__TAURI__.core.invoke('host_request',{request:{v:'aos-local/0.1',kind:'request',id:crypto.randomUUID(),op:'status',body:{}}}));
  const s=reply.result;
  assert.equal(s.nodes['main/model'].attempts.length,1);assert.equal(s.nodes['main/output'].attempts.length,0);
  assert.equal(fs.readdirSync(path.join(session,'runs')).length,1);
  fs.writeFileSync(path.join(__dirname,'window.json'),JSON.stringify({session,runId:s.runId,state:s.state,model:s.nodes['main/model'],output:s.nodes['main/output']},null,2));
  await p.screenshot({path:path.join(__dirname,'cutoff.png')});
 }finally{
  if(p)await p.evaluate(()=>window.__TAURI__.core.invoke('window_report',{report:{close:true}})).catch(()=>{});
  if(browser)await browser.close();proc.unref();
 }
})().catch(e=>{console.error(e);process.exitCode=1});
