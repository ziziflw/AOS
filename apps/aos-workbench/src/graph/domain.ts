import { ArrowDownToLine, BookOpenText, Boxes, BrainCircuit, FileInput, GitBranch, GitMerge, ListChecks, ScanLine, ShieldCheck } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'

export type Category = 'data' | 'model' | 'agent' | 'tool' | 'control'
export type PortType = 'Text' | 'Table' | 'Record'
type Pin = { id:string; label:string; type:PortType; side?:'top'|'bottom' }
export type Template = { title:string; label:string; category:Category; icon:LucideIcon; summary:string; parameter:string; value:string; inputs:Pin[]; outputs:Pin[] }
const pin = (id:string,label:string,type:PortType,side?:Pin['side']):Pin=>({id,label,type,side})
export const categories:Record<Category,{name:string;color:string;icon:LucideIcon}>={
 data:{name:'数据',color:'#69d6b7',icon:FileInput},model:{name:'模型',color:'#9faeff',icon:BrainCircuit},
 agent:{name:'Agent',color:'#dea0d1',icon:Boxes},tool:{name:'工具',color:'#7db6e4',icon:ScanLine},
 control:{name:'控制',color:'#efb974',icon:GitBranch}}
export const templates:Record<string,Template>={
 orders:{title:'订单数据',label:'读取订单',category:'data',icon:FileInput,summary:'orders.csv',parameter:'数据集',value:'orders.csv',inputs:[],outputs:[pin('rows','记录','Table')]},
 payments:{title:'支付流水',label:'读取支付',category:'data',icon:BookOpenText,summary:'payments.csv',parameter:'数据集',value:'payments.csv',inputs:[],outputs:[pin('rows','记录','Table')]},
 join:{title:'跨表核对',label:'跨表核对',category:'tool',icon:GitMerge,summary:'按订单编号关联',parameter:'关联字段',value:'order_id',inputs:[pin('orders','订单','Table'),pin('payments','支付','Table')],outputs:[pin('result','结果','Record')]},
 branch:{title:'异常分流',label:'条件分支',category:'control',icon:GitBranch,summary:'筛选金额或状态异常',parameter:'条件说明',value:'支付金额与订单金额不符',inputs:[pin('record','输入','Record')],outputs:[pin('exception','异常记录','Record','bottom'),pin('normal','正常记录','Record')]},
 gemma:{title:'投诉分析',label:'本地模型',category:'model',icon:BrainCircuit,summary:'Gemma 4 E4B',parameter:'模型标识',value:'google/gemma-4-e4b',inputs:[pin('context','上下文','Record','top')],outputs:[pin('text','建议','Text')]},
 review:{title:'人工复核',label:'人工复核',category:'control',icon:ShieldCheck,summary:'核查建议与关联证据',parameter:'核查要求',value:'核对订单、支付与投诉证据',inputs:[pin('text','建议','Text')],outputs:[pin('report','结论','Text')]},
 agent:{title:'任务代理',label:'任务代理',category:'agent',icon:Boxes,summary:'基于指令整理文本',parameter:'任务说明',value:'整理核查要点',inputs:[pin('text','任务','Text')],outputs:[pin('reply','答复','Text')]},
 validate:{title:'记录校验',label:'记录校验',category:'tool',icon:ListChecks,summary:'检查必需字段',parameter:'必需字段',value:'order_id',inputs:[pin('rows','输入','Table')],outputs:[pin('rows','记录','Table')]},
 output:{title:'文本输出',label:'文本输出',category:'data',icon:ArrowDownToLine,summary:'保留文本结果',parameter:'结果名称',value:'核查结果',inputs:[pin('text','结果','Text')],outputs:[]}
}
export type Point={x:number;y:number}
export type Step={id:string;kind:string;title:string;value:string;position:Point}
export type Link={id:string;source:string;target:string;sourceHandle:string;targetHandle:string}
export type Draft={schemaVersion:1;title:string;nodes:Step[];edges:Link[]}
export const makeStep=(kind:string, position:Point, id:string=crypto.randomUUID()):Step=>({id,kind,title:templates[kind].title,value:templates[kind].value,position})
export function sample():Draft {
 const nodes=[makeStep('orders',{x:0,y:0},'orders'),makeStep('payments',{x:0,y:156},'payments'),
 makeStep('join',{x:238,y:78},'join'),makeStep('branch',{x:476,y:78},'branch'),
 makeStep('gemma',{x:238,y:290},'gemma'),makeStep('review',{x:476,y:290},'review')]
 const wires=[['orders','rows','join','orders'],['payments','rows','join','payments'],['join','result','branch','record'],['branch','exception','gemma','context'],['gemma','text','review','text']]
 return {schemaVersion:1,title:'订单审计',nodes,edges:wires.map(([source,sourceHandle,target,targetHandle])=>({id:source+'-'+target,source,sourceHandle,target,targetHandle}))}
}
export function connectionError(doc:Draft,line:Omit<Link,'id'>):string|null{
 const src=doc.nodes.find(n=>n.id===line.source),dst=doc.nodes.find(n=>n.id===line.target)
 if(!src||!dst)return '连接端点不存在'
 const output=templates[src.kind].outputs.find(p=>p.id===line.sourceHandle),input=templates[dst.kind].inputs.find(p=>p.id===line.targetHandle)
 if(!output||!input||output.type!==input.type)return '端口类型不匹配'
 if(doc.edges.some(e=>e.target===dst.id&&e.targetHandle===input.id))return '该输入已连接'
 const seen=new Set([dst.id]),queue=[dst.id]
 while(queue.length){const n=queue.pop();if(n===src.id)return '连接将形成循环';for(const e of doc.edges){if(e.source===n&&!seen.has(e.target)){seen.add(e.target);queue.push(e.target)}}}
 return null
}
export function readDraft(raw:string):Draft {
 const doc=JSON.parse(raw) as Draft
 if(doc.schemaVersion!==1||typeof doc.title!=='string'||!Array.isArray(doc.nodes)||!Array.isArray(doc.edges)||doc.nodes.length>1000||doc.edges.length>5000)throw Error('草稿格式不兼容')
 const ids=new Set<string>()
 for(const n of doc.nodes){
   if(!Object.hasOwn(templates,n.kind)||typeof n.id!=='string'||!n.id||ids.has(n.id)||typeof n.title!=='string'||typeof n.value!=='string'||!Number.isFinite(n.position?.x)||!Number.isFinite(n.position?.y))throw Error('无效节点')
   ids.add(n.id)
 }
 const checked={...doc,edges:[] as Link[]},edgeIds=new Set<string>()
 for(const e of doc.edges){if(typeof e.id!=='string'||edgeIds.has(e.id)||connectionError(checked,e))throw Error('无效连线');checked.edges.push(e);edgeIds.add(e.id)}
 return doc
}
