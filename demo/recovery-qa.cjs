const assert=require('assert');module.exports=async function(page){
 const call=(op,body={})=>page.evaluate(({op,body})=>window.__TAURI__.core.invoke('host_request',{request:{v:'aos-local/0.1',kind:'request',id:crypto.randomUUID(),op,body}}),{op,body});
 const h=(await call('health')).result,w=h.sample.workflow;w.graph.nodes[0].typeId='agent.delegate';assert.equal((await call('load',{action:'validate',workflow:w})).error.code,'A2A_SERVICE_UNBOUND');
 assert.equal((await call('load',{action:'local-list',url:'https://example.invalid/v1'})).error.code,'LOCAL_ADDRESS_DENIED');
 await page.getByRole('button',{name:'载入审批示例',exact:true}).click();await page.getByTestId('run').click();await page.waitForFunction(()=>document.querySelector('[data-testid=run-state]').textContent.includes('等待审批'));
 const s=(await call('status')).result;assert((await call('host.crash-worker')).ok);assert((await call('host.start')).ok);const r=await call('recover');assert(r.ok);assert.equal(r.result.runId,s.runId);assert(Object.values(r.result.approvals).some(a=>a.status==='pending'));assert((await call('cancel')).ok);console.log('worker crash/recovery retained approval and run identity',s.runId)}
