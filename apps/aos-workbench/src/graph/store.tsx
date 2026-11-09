import {createContext,useCallback,useContext,useEffect,useRef,useState} from 'react'
import type {ReactNode} from 'react'
import {connectionError,makeStep,readDraft,sample,templates} from './domain'
import type {Draft,Link,Point,Step} from './domain'

const KEY='aos.workbench.demo.graph.v1'
function initial(){
 try{const s=localStorage.getItem(KEY);if(s)return {doc:readDraft(s),message:'已载入本地草稿'}}
 catch{return {doc:sample(),message:'本地草稿无法载入，已打开示例'}}
 return {doc:sample(),message:''}
}
function useDraft(){
 const [boot]=useState(initial)
 const [doc,setDoc]=useState(boot.doc), current=useRef(doc)
 const [selectedId,select]=useState<string|null>(doc.nodes.find(n=>n.kind==='gemma')?.id??null)
 const [message,notify]=useState(boot.message), [saved,markSaved]=useState(JSON.stringify(boot.doc))
 const [clipboard,storeCopy]=useState<Step|null>(null)
 const past=useRef<Draft[]>([]), future=useRef<Draft[]>([])
 const fitRef=useRef<null|(()=>void)>(null),focusRef=useRef<null|((p:Point)=>void)>(null)
 const replace=useCallback((d:Draft)=>{current.current=d;setDoc(d)},[])
 const update=useCallback((d:Draft)=>{past.current=[...past.current.slice(-79),current.current];future.current=[];replace(d)},[replace])
 const fit=useCallback(()=>fitRef.current?.(),[])
 const register=useCallback((fitFn:typeof fitRef.current,focusFn:typeof focusRef.current)=>{fitRef.current=fitFn;focusRef.current=focusFn},[])
 const selected=doc.nodes.find(n=>n.id===selectedId)??null
 useEffect(()=>{if(selectedId&&!doc.nodes.some(n=>n.id===selectedId))select(null)},[doc.nodes,selectedId])
 function undo(){const prev=past.current.pop();if(prev){future.current.push(current.current);replace(prev);notify('已撤销')}}
 function redo(){const next=future.current.pop();if(next){past.current.push(current.current);replace(next);notify('已重做')}}
 function add(kind:string,drop?:Point){
  if(!Object.hasOwn(templates,kind))return
  const d=current.current, last=d.nodes[d.nodes.length-1]
  const position=drop??{x:(last?.position.x??-50)+50,y:(last?.position.y??-64)+64}
  const n=makeStep(kind,position);update({...d,nodes:[...d.nodes,n]});select(n.id);notify('已添加「'+n.title+'」')
  if(!drop)requestAnimationFrame(()=>focusRef.current?.(position))
 }
 function edit(id:string,patch:Partial<Pick<Step,'title'|'value'|'position'>>){
  const d=current.current,n=d.nodes.find(n=>n.id===id)
  if(!n||JSON.stringify({...n,...patch})===JSON.stringify(n))return
  update({...d,nodes:d.nodes.map(s=>s.id===id?{...s,...patch}:s)})
 }
 function connect(line:Omit<Link,'id'>){const d=current.current;const error=connectionError(d,line);if(error){notify(error);return}
  update({...d,edges:[...d.edges,{...line,id:crypto.randomUUID()}]});notify('已连接端口')
 }
 function remove(ids:string[],edges:string[]=[]){
  const d=current.current;if(!ids.length&&!edges.length)return
  update({...d,nodes:d.nodes.filter(n=>!ids.includes(n.id)),edges:d.edges.filter(e=>!ids.includes(e.source)&&!ids.includes(e.target)&&!edges.includes(e.id))})
  notify('已删除所选内容')
 }
 function save(){try{localStorage.setItem(KEY,JSON.stringify(current.current));markSaved(JSON.stringify(current.current));notify('本地草稿已保存');return true}catch{notify('草稿保存失败，请检查浏览器存储');return false}}
 function load(){try{const text=localStorage.getItem(KEY);if(!text){notify('尚无已保存的草稿');return}const d=readDraft(text);update(d);markSaved(JSON.stringify(d));select(null);notify('已打开本地草稿');requestAnimationFrame(fit)}catch{notify('草稿无法读取，保留当前画布')}}
 function newGraph(){update({schemaVersion:1,title:'未命名工作流',nodes:[],edges:[]});select(null);notify('已新建本地草稿')}
 function restoreSample(){update(sample());select('gemma');notify('已打开订单审计示例');requestAnimationFrame(fit)}
 function copy(){if(selected){storeCopy({...selected});notify('已复制节点')}}
 function paste(){if(!clipboard)return;const n={...clipboard,id:crypto.randomUUID(),position:{x:clipboard.position.x+32,y:clipboard.position.y+32}}
  update({...current.current,nodes:[...current.current.nodes,n]});select(n.id);storeCopy(n);notify('已粘贴节点')
 }
 return {doc,title:doc.title,dirty:JSON.stringify(doc)!==saved,selectedId,selected,message,select,notify,nodeCount:doc.nodes.length,edgeCount:doc.edges.length,
 canUndo:past.current.length>0,canRedo:future.current.length>0,canPaste:!!clipboard,undo,redo,add,edit,remove,removeSelected:()=>selectedId&&remove([selectedId]),
 connect,save,load,newGraph,restoreSample,fit,register,copy,paste}
}
const GraphContext=createContext<ReturnType<typeof useDraft>|null>(null)
export function GraphProvider({children}:{children:ReactNode}){const state=useDraft();return <GraphContext.Provider value={state}>{children}</GraphContext.Provider>}
export function useGraph(){const value=useContext(GraphContext);if(!value)throw Error('缺少 GraphProvider');return value}

