const invoke=window.__TAURI__.core.invoke,view=document.querySelector('#view'),err=document.querySelector('#error');
let seq=0;
async function raw(op,body={}){return invoke('host_request',{request:{v:'aos-local/0.1',kind:'request',id:'window-'+(++seq),op,body}})}
async function call(op,body={}){let r=await raw(op,body);if(!r.ok)throw Error(r.error.code);view.textContent=JSON.stringify(r.result,null,2);return r.result}
function action(id,f){document.querySelector('#'+id).onclick=async()=>{try{err.textContent='';await f()}catch(e){err.textContent=String(e)}}}
action('connect',()=>call('host.start'));
action('run',async()=>{let p=await call('load',{builtin:document.querySelector('#builtin').value});await call('create',{token:p.token})});
action('refresh',()=>call('status'));action('cancel',()=>call('cancel'));action('stop',()=>call('host.stop',{mode:'suspend'}));
action('recover',()=>call('recover'));
let eventCursor=0;action('events',async()=>{const p=await call('events',{after:eventCursor});eventCursor=p.lastSeq});
async function approve(decision){let p=await call('approvals');if(!p.length)throw Error('没有待审批操作');return call('approve',{approvalId:p[0].id,fingerprint:p[0].fingerprint,decision})}
action('approve',()=>approve(true));action('deny',()=>approve(false));
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
async function selftest(){let checks=[];function check(label,actual,expected){checks.push({label,actual,expected,passed:JSON.stringify(actual)===JSON.stringify(expected)});if(!checks.at(-1).passed)throw Error(label)}
try {
 check('real WebView global API',typeof window.__TAURI__.core.invoke,'function');
 await call('host.start');let h=await call('health');check('Python authority',h.authority,'C1/SQLite');
 let p=await call('load',{builtin:'effect'});await call('create',{token:p.token});let s;
 for(let i=0;i<200;i++){s=await call('status');if(s.state==='waiting-approval')break;await sleep(30)}
 check('backend blocks before approval',s.state,'waiting-approval');check('unauthorized command',(await raw('exec',{command:'denied'})).error.code,'UNKNOWN_COMMAND');
 let a=(await call('approvals'))[0];check('stale approval rejected',(await raw('approve',{approvalId:a.id,fingerprint:'invalid',decision:true})).ok,false);
 await approve(true);for(let i=0;i<200;i++){s=await call('status');if(s.state==='succeeded')break;await sleep(30)}
 check('approved workflow completes',s.state,'succeeded');let events=await call('events',{after:0});check('actual C1 events visible',events.events.length>0,true);
 let denied=false;try{await invoke('plugin:fs|read_text_file',{path:'denied'})}catch(e){denied=true}check('no arbitrary file plugin',denied,true);
 let stop=await call('host.stop',{mode:'suspend'});check('coordinated close',stop.durable,true);
 await invoke('window_report',{report:{surface:'real Tauri WebView2 -> Rust -> framed Python IPC',checks,passed:checks.every(x=>x.passed),runId:s.runId,finalSeq:s.seq,userAgent:navigator.userAgent}});
}catch(e){err.textContent=String(e);await invoke('window_report',{report:{passed:false,checks,error:String(e)}})}}
// Setup evaluation and asset initialization may race; wait before checking the explicit harness flag.
setTimeout(()=>{if(window.__AOS_SELFTEST__)selftest()},500);
