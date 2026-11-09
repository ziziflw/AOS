const http=require('http'), fs=require('fs'),path=require('path'),assert=require('assert');
module.exports=async function(page,app){
 const root=path.join(app,'app/experiments/p0-08'),dir=path.join(root,'workspace');fs.mkdirSync(dir,{recursive:true});
 await page.getByLabel('SDK场景',{exact:true}).selectOption('p08.ollama.text');
 await page.getByTestId('run').click();await page.waitForFunction(()=>document.querySelector('[data-testid=run-state]').textContent.includes('失败'));
 const status=async()=> (await page.evaluate(()=>window.__TAURI__.core.invoke('host_request',{request:{v:'aos-local/0.1',kind:'request',id:crypto.randomUUID(),op:'status',body:{}}}))).result;
 assert.equal((await status()).nodes['main/model'].error.code,'LOCAL_CONNECTION_NOT_CONFIGURED');
 let posts=0;const server=http.createServer((req,res)=>{res.setHeader('content-type','application/json');if(req.url==='/v1/models')res.end(JSON.stringify({object:'list',data:[{id:'qa-local',object:'model',created:1,owned_by:'qa'}]}));else if(req.url==='/v1/chat/completions'){posts++;res.end(JSON.stringify({id:'qa',object:'chat.completion',created:1,model:'qa-local',choices:[{index:0,message:{role:'assistant',content:'本机协议夹具结果'},finish_reason:'stop'}],usage:{prompt_tokens:9,completion_tokens:5,total_tokens:14}}))}else{res.statusCode=404;res.end('{}')}});
 await new Promise(r=>server.listen(0,'127.0.0.1',r));try{const url='http://127.0.0.1:'+server.address().port+'/v1';for(const [kind,tid] of [['Ollama','p08.ollama.text'],['LM Studio','p08.lmstudio.text']]){
 await page.getByRole('button',{name:'本地模型连接',exact:true}).click();await page.getByLabel('本地服务').selectOption(kind);await page.getByLabel('回环地址').fill(url);await page.getByRole('button',{name:'测试连接并获取模型'}).click();await page.waitForFunction(()=>document.querySelector('dialog [role=status]').textContent.includes('连接成功'));await page.getByRole('button',{name:'保存连接',exact:true}).click();await page.waitForFunction(()=>document.querySelector('dialog [role=status]').textContent.includes('已保存'));await page.getByRole('button',{name:'关闭设置'}).click();await page.getByLabel('SDK场景',{exact:true}).selectOption(tid);
 const prior=(await status()).runId;await page.getByTestId('run').click();let s;for(let i=0;i<100;i++){s=await status();if(s.runId!==prior&&['failed','succeeded','unknown'].includes(s.state))break;await page.waitForTimeout(100)}assert.equal(s.state,'succeeded',JSON.stringify(s.nodes['main/model'].error));assert.equal(s.scopes.main.result,'本机协议夹具结果');console.log(kind,'synthetic HTTP passed',s.runId)}assert.equal(posts,2)}finally{server.close()}
}

