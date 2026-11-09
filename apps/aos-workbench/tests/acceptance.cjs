/* Run against the isolated loopback dev server. All test data lives in disposable browser contexts. */
const {chromium}=require(process.env.AOS_PLAYWRIGHT || 'C:/Users/Administrator/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright')
const path=require('node:path'),fs=require('node:fs'),assert=require('node:assert/strict')
const out=path.resolve(__dirname,'../docs/evidence'),base='http://127.0.0.1:4177'
const executablePath=process.env.AOS_EDGE || 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'
const report={browser:'',checks:[],screens:[],pageErrors:[],externalRequests:[]}
const runKey='aos.workbench.preview.layout'
async function test(name,fn){try{const observed=await fn();report.checks.push({name,status:'PASS',observed});console.log('PASS',name)}catch(error){const reason=String(error).slice(0,550);report.checks.push({name,status:'FAIL',reason});console.log('FAIL',name,reason)}}
function tab(page,id){return page.locator('[data-panel-tab="'+id+'"]')}
const groups=p=>p.locator('.dv-groupview').count()
async function command(page,id){await page.keyboard.press('Control+k');await page.locator('#command-'+id).click()}
async function menu(page,name,label){await page.getByRole('button',{name,exact:true}).click();await page.getByRole('menuitem',{name:label,exact:true}).click()}
async function ready(page){await page.goto(base);await page.waitForSelector('.react-flow__node');await page.waitForFunction(()=>document.querySelectorAll('.react-flow__node').length>=6);await page.evaluate(()=>document.fonts.ready);await page.waitForTimeout(250)}
async function drag(page,from,to){await page.mouse.move(from.x,from.y);await page.mouse.down();await page.mouse.move(from.x+8,from.y+2,{steps:4});await page.mouse.move(to.x,to.y,{steps:26});await page.mouse.move(to.x+1,to.y+1);await page.waitForTimeout(125);await page.mouse.up();await page.waitForTimeout(175)}
async function main(){
 fs.mkdirSync(out,{recursive:true})
 const browser=await chromium.launch({executablePath,headless:true});report.browser=browser.version()
 try{
  for(const [name,width,height] of [['desktop',1440,900],['compact',960,720],['mobile',390,844]]){
   const context=await browser.newContext({viewport:{width,height},deviceScaleFactor:1});const page=await context.newPage()
   page.on('pageerror',e=>report.pageErrors.push(e.message))
   try{await ready(page);await page.screenshot({path:path.join(out,name+'.png')})
    report.screens.push({name,width,height,overflow:await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),
      panels:await page.locator('[data-panel-tab]').allTextContents(),canvasWidth:await page.locator('.ag-flow').evaluate(el=>Math.round(el.getBoundingClientRect().width))})
   }finally{await context.close()}
  }
  const context=await browser.newContext({viewport:{width:1440,height:900}});const p=await context.newPage();p.setDefaultTimeout(4500)
  p.on('pageerror',e=>report.pageErrors.push(e.message))
  p.on('request',r=>{if(/^https?:/.test(r.url()) && !(new URL(r.url()).origin===base))report.externalRequests.push(new URL(r.url()).origin)})
  await ready(p)
  const button=name=>p.getByRole('button',{name,exact:true})
  await test('演示状态与禁用运行',async()=>{assert(await button('运行工作流').isDisabled());assert((await p.locator('.statusbar').innerText()).includes('演示模式'));return await button('运行工作流').getAttribute('title')})
  await test('分类、查找、添加与修改节点',async()=>{
   const count=await p.locator('.react-flow__node').count()
   const row=p.locator('.ag-library-row').filter({hasText:'任务代理'})
   await p.getByRole('button',{name:/^Agent$/i}).click()
   await p.getByLabel('搜索组件').fill('任务代理');await row.click()
   await p.getByLabel('节点名称').fill('复核测试草稿');await p.getByLabel('节点名称').press('Enter')
   assert.equal(await p.locator('.react-flow__node').count(),count+1);assert(await p.locator('.react-flow__node').filter({hasText:'复核测试草稿'}).count()===1)
   return {before:count,after:count+1,edited:'复核测试草稿'}
  })
  await test('撤销重做与保存重载',async()=>{await button('撤销').click();assert.equal(await p.locator('.react-flow__node').filter({hasText:'复核测试草稿'}).count(),0);await button('重做').click();await button('保存草稿').click();await ready(p);assert.equal(await p.locator('.react-flow__node').filter({hasText:'复核测试草稿'}).count(),1);return '编辑后的名称在新挂载中恢复'})
  await test('标签合并与再分屏',async()=>{
   const original=await groups(p);assert.equal(original,3)
   const source=tab(p,'inspector').locator('span').first()
   await source.dragTo(tab(p,'catalog').locator('span').first())
   await p.waitForFunction(()=>document.querySelectorAll('.dv-groupview').length===2)
   const group=tab(p,'canvas').locator('xpath=ancestor::*[contains(concat(" ",normalize-space(@class)," ")," dv-groupview ")][1]')
   const target=await group.locator('.dv-content-container').boundingBox(),s=await source.boundingBox()
   await drag(p,{x:s.x+s.width/2,y:s.y+s.height/2},{x:target.x+target.width*.48,y:target.y+target.height-15})
   await p.waitForFunction(()=>document.querySelectorAll('.dv-groupview').length===3)
   const i=await tab(p,'inspector').boundingBox(),c=await tab(p,'canvas').boundingBox()
   assert(i.y>c.y+60);return {groupCounts:[3,2,3],canvasTabY:c.y,inspectorTabY:i.y}
  })
  await test('边界缩放',async()=>{
   const panel=()=>p.locator('.ag-catalog').boundingBox()
   const before=await panel();assert(before)
   const sash=await p.locator('.dv-sash').evaluateAll(els=>els.map(el=>el.getBoundingClientRect().toJSON()).find(b=>b.height>200&&b.width<20))
   assert(sash);await drag(p,{x:sash.x+sash.width/2,y:sash.y+sash.height*.5},{x:sash.x+50,y:sash.y+sash.height*.5});const after=await panel()
   assert(Math.abs(after.width-before.width)>16);return {before:before.width,after:after.width}
  })
  await test('关闭并通过窗口菜单重开',async()=>{await tab(p,'inspector').hover();await button('关闭属性检查器').click();assert.equal(await tab(p,'inspector').count(),0);await menu(p,'窗口','属性检查器');assert.equal(await tab(p,'inspector').count(),1);return '0 → 1 个同 ID 面板'})
  await test('命令搜索、无匹配、重开与聚焦',async()=>{await tab(p,'inspector').hover();await button('关闭属性检查器').click();await p.keyboard.press('Control+k');await p.getByLabel('搜索命令或窗口').fill('unmatched-qa');assert(await p.getByText('没有匹配的命令').isVisible());await p.getByLabel('搜索命令或窗口').fill('属性检查器');await p.keyboard.press('Enter');assert(await tab(p,'inspector').count()===1);await command(p,'inspector');assert(await tab(p,'inspector').count()===1);return 'Ctrl+K 与 Enter 打开现有面板，相同 ID 只出现一次'})
  await test('预设切换、保存、自定义布局恢复',async()=>{
   for(const name of ['调试','配置']){await button(name).click();const confirm=button('切换预设');if(await confirm.isVisible())await confirm.click();assert.equal(await button(name).getAttribute('aria-pressed'),'true')}
   await tab(p,'catalog').hover();await button('关闭组件目录').click();await menu(p,'窗口','保存工作区布局')
   const layout=await p.evaluate(k=>JSON.parse(localStorage.getItem(k)),runKey);assert.equal(layout.schemaVersion,1);assert.equal(layout.preset,'配置');assert(!layout.dockview.panels.catalog)
   await ready(p);assert.equal(await tab(p,'catalog').count(),0);assert(await p.getByText('已恢复保存的布局').isVisible())
   return {preset:layout.preset,panels:Object.keys(layout.dockview.panels)}
  })
  await test('重置保护与布局损坏回退',async()=>{await menu(p,'窗口','恢复预设布局');await button('取消').click();assert.equal(await tab(p,'catalog').count(),0)
   await p.evaluate(k=>localStorage.setItem(k,'{broken'),runKey);await ready(p)
   assert(await p.getByText('布局无法读取，已恢复编排预设。').isVisible());assert.equal(await tab(p,'catalog').count(),1);assert.equal(await p.locator('.react-flow__node').filter({hasText:'复核测试草稿'}).count(),1)
   return '编排布局恢复，已保存图内容保留'
  })
  await context.close()
 }finally{await browser.close();fs.writeFileSync(path.join(out,'browser.json'),JSON.stringify(report,null,2))}
 if(report.checks.some(c=>c.status==='FAIL')||report.pageErrors.length||report.externalRequests.length)process.exitCode=1
}
main().catch(err=>{console.error(err.message);process.exitCode=1})

