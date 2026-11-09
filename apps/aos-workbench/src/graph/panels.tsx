import {useState} from 'react'
import {ChevronRight, Search, X} from 'lucide-react'
import {categories,templates} from './domain'
import type {Category} from './domain'
import {useGraph} from './store'

const sections: {key:Category;label:string}[]=[
  {key:'data',label:'输入与输出'},{key:'model',label:'本地模型'},{key:'agent',label:'Agent'},
  {key:'tool',label:'数据处理'},{key:'control',label:'流程控制'}
]
export function MaterialIcon({kind}:{kind:string}){
 const t=templates[kind]
 const asset=({branch:'icon-condition.svg',join:'icon-script.png',validate:'icon-script.png',orders:'icon-variable.png',payments:'icon-variable.png'} as Record<string,string>)[kind]
 return asset?<img className="material-icon" src={'./materials/'+asset} alt=""/>:<t.icon size={16} aria-hidden/>
}
export function Catalog(){
 const g=useGraph(),[query,setQuery]=useState(''),[category,setCategory]=useState<Category|null>(null)
 const rows=Object.entries(templates).filter(([key,t])=>(key+t.title+t.label+t.value).toLowerCase().includes(query.trim().toLowerCase()))
 return <div className="library"><label className="filter"><Search size={15}/><input aria-label="搜索组件" placeholder="搜索" value={query} onChange={e=>setQuery(e.target.value)}/>{query&&<button aria-label="清除搜索" onClick={()=>setQuery('')}><X size={13}/></button>}</label>
 <h2>组件</h2>{sections.map(({key,label})=>{const Icon=categories[key].icon;const items=rows.filter(([,t])=>t.category===key)
 if(query&&!items.length)return null
 const expanded=!!query||category===key
 return <section key={key}><button className="category" aria-expanded={expanded} onClick={()=>setCategory(expanded?null:key)}><Icon size={16}/>{label}<ChevronRight size={14} className={expanded?'expanded':''}/></button>
 {expanded&&items.map(([k,t])=><button key={k} className="component" draggable onDragStart={e=>{e.dataTransfer.setData('application/x-aos-component',k);e.dataTransfer.effectAllowed='copy'}} aria-label={'添加'+t.label} onClick={()=>g.add(k)}><MaterialIcon kind={k}/>{t.label}</button>)}</section>})}{query&&!rows.length&&<p>无匹配组件</p>}</div>
}
export function Inspector(){
 const g=useGraph(),s=g.selected
 if(!s)return null
 return <div className="editor-form"><h2>节点属性</h2><label>名称<input aria-label="节点名称" value={s.title} maxLength={120} onChange={e=>g.edit(s.id,{title:e.target.value})}/></label>
 <label>{templates[s.kind].parameter}<textarea aria-label={templates[s.kind].parameter} value={s.value} maxLength={500} onChange={e=>g.edit(s.id,{value:e.target.value})}/></label></div>
}
