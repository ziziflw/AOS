/* Exercise the separately built, local-data-only Tauri preview. */
const fs = require('node:fs')
const path = require('node:path')
const child = require('node:child_process')
const assert = require('node:assert/strict')
const crypto = require('node:crypto')
const {chromium} = require(process.env.AOS_PLAYWRIGHT || 'C:/Users/Administrator/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright')
const base = path.resolve(__dirname, '..')
const exe = path.join(base, '.desktop-preview/AOS-UI.exe')
const root = path.join(base, '.desktop-preview/qa')
const session = path.join(root, 'evidence',String(Date.now()))
const out = path.join(base, 'docs/evidence')
const wait = ms => new Promise(resolve => setTimeout(resolve, ms))
async function main() {
  let existing = await fetch('http://127.0.0.1:9238/json/version').then(()=>true,()=>false)
  if (existing) throw new Error('Test debugging port in use')
  fs.mkdirSync(session,{recursive:true});fs.mkdirSync(out,{recursive:true})
  const proc = child.spawn(exe,[root,session,'test'],{stdio:'ignore'})
  let browser,page
  const errors=[]
  try{
    for(let i=0;i<80&&!browser;i++){
      try{browser=await chromium.connectOverCDP('http://127.0.0.1:9238')}catch{await wait(150)}
    }
    assert.ok(browser,'WebView2 debugging session missing')
    page=browser.contexts()[0].pages()[0];page.on('pageerror',e=>errors.push(e.message))
    await page.getByRole('heading',{name:'订单审计',exact:true}).waitFor({timeout:9000})
    assert.ok(await page.evaluate(()=>Boolean(window.__TAURI__?.core && window.__AOS_SELFTEST__)))
    const n=await page.locator('.react-flow__node').count()
    assert.ok(n>=6)
    const btn=name=>page.getByRole('button',{name,exact:true})
    const nodes=page.locator('.react-flow__node')
    await page.evaluate(()=>document.fonts.ready)
    await wait(300)
    assert.equal(await page.locator('.studio footer,[role=tooltip],.studio [title],.studio aside:not(.side)').count(),0)
    assert.ok(await page.getByLabel('搜索组件').isVisible())
    assert.ok(await page.locator('.material-icon').evaluateAll(imgs=>imgs.every(img=>img.complete&&img.naturalWidth>0)))
    await page.screenshot({path:path.join(out,'langflow-open.png')})
    await btn('收起侧栏').click()
    await page.waitForTimeout(120)
    assert.equal(await page.locator('.side').count(),0)
    await page.screenshot({path:path.join(out,'langflow-canvas.png')})
    await btn('组件库').click()
    await page.getByLabel('搜索组件').fill('本地模型')
    await btn('添加本地模型').click()
    assert.equal(await nodes.count(),n+1)
    await btn('编辑节点').click()
    await page.getByLabel('节点名称').fill('测试草稿')
    await btn('保存草稿').click()
    await page.reload()
    await nodes.filter({hasText:'测试草稿'}).waitFor()
    await wait(350)
    await nodes.filter({hasText:'测试草稿'}).locator('.card-name').dblclick()
    assert.equal(await page.getByLabel('节点名称').inputValue({timeout:1400}),'测试草稿')
    assert.deepEqual(errors,[])
    const bridge=path.join(session,'window-bridge.jsonl')
    const businessCalls=fs.existsSync(bridge)?fs.readFileSync(bridge,'utf8').trim():null
    assert.ok(!businessCalls,'Unexpected business calls in mock UI')
    const result={window:'Tauri / WebView2',title:await page.title(),url:page.url(),size:await page.evaluate(()=>[innerWidth,innerHeight]),nodes:n,
        catalogToggle:true,editAndReload:true,noPermanentHints:true,pageErrors:errors,businessCalls:0,exeSHA256:crypto.createHash('sha256').update(fs.readFileSync(exe)).digest('hex')}
    fs.writeFileSync(path.join(out,'langflow-desktop.json'),JSON.stringify(result,null,2));console.log(result)
  }finally{
    if(page)await page.evaluate(()=>window.__TAURI__.core.invoke('window_report',{report:{close:true}})).catch(()=>{})
    if(browser)await browser.close()
    if(proc.exitCode===null){await wait(500);if(proc.exitCode===null)proc.kill()}
  }
}
main().catch(e=>{console.error(e);process.exitCode=1})

