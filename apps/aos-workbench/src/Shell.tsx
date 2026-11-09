import {useEffect,useState} from 'react'
import * as Menu from '@radix-ui/react-dropdown-menu'
import {Blocks,Check,ChevronDown,FilePlus2,FolderOpen,GitFork,PanelLeftClose,Redo2,Save,SlidersHorizontal,Undo2,Workflow} from 'lucide-react'
import {Canvas,Catalog,Inspector,useGraph} from './graph'
type Panel='library'|'files'|'edit'|null
export function Shell(){
 const g=useGraph()
 const [panel,show]=useState<Panel>(()=>innerWidth>=800?'library':null)
 const [saved,setSaved]=useState(false)
 useEffect(()=>setSaved(false),[g.doc])
 const toggle=(p:Panel)=>show(panel===p?null:p)
 function save(){setSaved(g.save())}
 function replace(action:()=>void){action();show('files')}
 const actions=[
  {label:'新建草稿',run:()=>replace(g.newGraph)},{label:'打开已保存草稿',run:()=>replace(g.load)},
  {label:'编辑节点',disabled:!g.selected,run:()=>show('edit')},{label:'撤销',disabled:!g.canUndo,run:g.undo},{label:'重做',disabled:!g.canRedo,run:g.redo},
  {label:'复制节点',disabled:!g.selected,run:g.copy},{label:'粘贴节点',disabled:!g.canPaste,run:g.paste},{label:'删除节点',disabled:!g.selected,run:g.removeSelected},
  {label:'适配画布',run:g.fit}
 ]
 useEffect(()=>{
  function key(e:KeyboardEvent){
   if(e.isComposing||e.defaultPrevented)return
   const ctrl=e.ctrlKey||e.metaKey,k=e.key.toLowerCase()
   if(ctrl&&k==='s'){e.preventDefault();save();return}
   if((e.target as HTMLElement)?.closest('input,textarea,[contenteditable=true]'))return
   if(k==='escape'){show(null);return}
   if(k==='/'){e.preventDefault();show('library');requestAnimationFrame(()=>document.querySelector<HTMLInputElement>('[aria-label="搜索组件"]')?.focus());return}
   const label=ctrl?({z:e.shiftKey?'重做':'撤销',y:'重做',c:'复制节点',v:'粘贴节点'} as Record<string,string>)[k]:k==='delete'?'删除节点':k==='enter'?'编辑节点':''
   const a=actions.find(a=>a.label===label);if(a&&!a.disabled){e.preventDefault();a.run()}
  }
  window.addEventListener('keydown',key);return()=>window.removeEventListener('keydown',key)
 })
 const err=/失败|无法|不匹配|循环|该输入已连接|不存在/.test(g.message)
 return <main className="studio"><header className="app-head"><Workflow aria-label="AOS" size={21}/><div className="breadcrumb"><span>AOS Studio</span><i>/</i><span className="flow-symbol"><GitFork size={13}/></span><h1>{g.title}</h1>{g.dirty&&<b aria-label="未保存"/>}</div></header>
 <div className="stage"><nav className="rail" aria-label="侧栏">
 <button aria-label="组件库" aria-pressed={panel==='library'} onClick={()=>toggle('library')}><Blocks/></button>
 <button aria-label="本地草稿" aria-pressed={panel==='files'} onClick={()=>toggle('files')}><FolderOpen/></button>
 <button aria-label="编辑节点" disabled={!g.selected} aria-pressed={panel==='edit'} onClick={()=>toggle('edit')}><SlidersHorizontal/></button>
 <hr/><button aria-label="撤销" disabled={!g.canUndo} onClick={g.undo}><Undo2/></button><button aria-label="重做" disabled={!g.canRedo} onClick={g.redo}><Redo2/></button></nav>
 {panel&&<aside className="side">{panel==='library'?<Catalog/>:panel==='edit'?<Inspector/>:<div className="files"><h2>本地草稿</h2><button onClick={g.load}><FolderOpen/>打开已保存草稿</button><button onClick={g.restoreSample}><GitFork/>订单审计示例</button><button onClick={g.newGraph}><FilePlus2/>新建草稿</button></div>}
 <button className="collapse" aria-label="收起侧栏" onClick={()=>show(null)}><PanelLeftClose size={16}/></button></aside>}
 <section className="canvas-host"><Canvas onInspect={()=>show('edit')}/><div className="actions"><button onClick={save} aria-label="保存草稿">{saved?<Check/>:<Save/>}保存</button><Menu.Root><Menu.Trigger aria-label="更多操作"><ChevronDown/></Menu.Trigger><Menu.Portal><Menu.Content align="end" sideOffset={5} className="actions-menu">{actions.map(a=><Menu.Item key={a.label} disabled={a.disabled} onSelect={a.run}>{a.label}</Menu.Item>)}</Menu.Content></Menu.Portal></Menu.Root></div>
 {err&&<span className="error-line" role="alert">{g.message}</span>}</section></div></main>
}
