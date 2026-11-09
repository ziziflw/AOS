import {memo,useCallback,useEffect,useMemo,useRef,useState} from 'react'
import {Background,Handle,Panel,Position,ReactFlow,ReactFlowProvider,useNodesState,useReactFlow,useViewport} from '@xyflow/react'
import type {Connection,Edge,Node,NodeProps} from '@xyflow/react'
import {Focus,Minus,Plus} from 'lucide-react'
import '@xyflow/react/dist/style.css'
import {connectionError,templates} from './domain'
import type {Draft,Step} from './domain'
import {MaterialIcon} from './panels'
import {useGraph} from './store'

type StepNode=Node<{step:Step},'step'>
const colors={Text:'#7571ec',Table:'#de3987',Record:'#48a6a0'}
const NodeCard=memo(function NodeCard({data}:NodeProps<StepNode>){
 const s=data.step,t=templates[s.kind]
 return <div className="flow-card"><div className="card-name"><MaterialIcon kind={s.kind}/><strong>{s.title}</strong></div>
 <div className="card-field">{s.value}</div>
 {(['target','source'] as const).flatMap(type=>{
  const pins=type==='target'?t.inputs:t.outputs
  return pins.map((p,i)=><Handle key={type+p.id} id={p.id} type={type} aria-label={p.label} position={p.side==='top'?Position.Top:p.side==='bottom'?Position.Bottom:type==='target'?Position.Left:Position.Right}
    style={{background:colors[p.type],...(!p.side&&pins.length>1?{top:(34+i*36)+'%'}:{})}}/>)
 })}
 </div>
})
const nodeTypes={step:NodeCard}
const project=(d:Draft,selected:string|null):StepNode[]=>d.nodes.map(s=>({id:s.id,position:s.position,data:{step:s},type:'step',ariaLabel:s.title,selected:selected===s.id}))
function Surface({onInspect}:{onInspect:()=>void}){
 const g=useGraph(),flow=useReactFlow<StepNode,Edge>(),view=useViewport()
 const [nodes,setNodes,onNodesChange]=useNodesState(project(g.doc,g.selectedId)),[picked,setPicked]=useState<string|null>(null)
 const invalid=useRef('')
 useEffect(()=>{
  setNodes(previous=>{
   const byId=new Map(previous.map(n=>[n.id,n]))
   return project(g.doc,g.selectedId).map(n=>({...byId.get(n.id),...n}))
  })
 },[g.doc,g.selectedId,setNodes])
 const fit=useCallback(()=>{void flow.fitView({padding:.20,maxZoom:1.06})},[flow])
 useEffect(()=>{g.register(fit,p=>{void flow.setCenter(p.x+100,p.y+40,{zoom:1})});return()=>g.register(null,null)},[g.register,fit,flow])
 const edges=useMemo(()=>g.doc.edges.map(e=>({...e,type:'default',selected:picked===e.id,interactionWidth:16,style:{stroke:picked===e.id?'#7571cd':'#a7acb8',strokeWidth:picked===e.id?2.3:1.6}})),[g.doc.edges,picked])
 const ok=(e:Connection|Edge)=>{invalid.current=connectionError(g.doc,{source:e.source,target:e.target,sourceHandle:e.sourceHandle??'',targetHandle:e.targetHandle??''})||'';return !invalid.current}
 return <div className="flow-space" aria-label="工作流画布" onDragOver={e=>{if(e.dataTransfer.types.includes('application/x-aos-component'))e.preventDefault()}} onDrop={e=>{const kind=e.dataTransfer.getData('application/x-aos-component');if(kind){e.preventDefault();g.add(kind,flow.screenToFlowPosition({x:e.clientX,y:e.clientY}))}}}>
 <ReactFlow<StepNode,Edge> nodeTypes={nodeTypes} nodes={nodes} edges={edges} fitView fitViewOptions={{padding:.20,maxZoom:1.06}} minZoom={.22} maxZoom={2.5} zoomOnDoubleClick={false} proOptions={{hideAttribution:true}} deleteKeyCode={null}
 onNodesChange={changes=>{onNodesChange(changes);for(const c of changes){if(c.type==='position'&&c.dragging===false&&c.position)g.edit(c.id,{position:c.position})}}}
 onNodeClick={(_,n)=>{g.select(n.id);setPicked(null)}} onNodeDoubleClick={(_,n)=>{g.select(n.id);onInspect()}} onEdgeClick={(_,e)=>{setPicked(e.id);g.select(null)}}
 onKeyDown={e=>{if(picked&&e.key==='Delete'){e.preventDefault();g.remove([],[picked]);setPicked(null)}}}
 onPaneClick={()=>{g.select(null);setPicked(null)}} onConnectStart={()=>{invalid.current=''}} onConnectEnd={()=>{if(invalid.current)g.notify(invalid.current)}}
 isValidConnection={ok} onConnect={e=>g.connect({...e,sourceHandle:e.sourceHandle??'',targetHandle:e.targetHandle??''})}>
 <Background gap={19} size={1} color="#b6b7c4"/>
 <Panel position="bottom-center"><div className="view-tools"><button aria-label="缩小" onClick={()=>flow.zoomOut()}><Minus/></button><button aria-label="重置为百分之百" onClick={()=>flow.zoomTo(1)}>{Math.round(view.zoom*100)}%</button><button aria-label="放大" onClick={()=>flow.zoomIn()}><Plus/></button><i/><button aria-label="适配画布" onClick={fit}><Focus/></button></div></Panel>
 </ReactFlow></div>
}
export function Canvas(props:{onInspect?:()=>void}){return <ReactFlowProvider><Surface onInspect={props.onInspect??(()=>{})}/></ReactFlowProvider>}

