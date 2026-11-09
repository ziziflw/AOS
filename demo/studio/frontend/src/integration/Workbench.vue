<script setup>
import {ref,computed,watch} from 'vue'
import {VueFlow,Handle,Position} from '@vue-flow/core'
import {Background} from '@vue-flow/background'
import variableIcon from '../../../../../apps/aos-workbench/public/materials/icon-variable.png'
const glyphs=import.meta.glob("./icons/*.svg",{eager:true,import:"default"})
const glyph=k=>glyphs["./icons/"+k+".svg"]
const {w}=defineProps({w:{type:Object,required:true}})
const panel=ref('组件'),group=ref(''),file=ref(),pick=ref(null),localError=ref('')
const all=import.meta.glob('../../../../../examples/workflows/*.json',{eager:true,import:'default'})
const examples=Object.entries(all).filter(([path])=>path.endsWith('.workflow.json')).map(([path,workflow])=>({
 code:path.split('/').pop().split('.')[0],workflow,layout:all[path.replace('.workflow.json','.layout.json')]}))
const ready=computed(()=>w.connection==='C1 已连接')
async function show(p){panel.value=p;if(p==='文件'&&ready.value)await w.refresh();if(p==='模型'&&ready.value)await w.readConnection()}
function toggle(p){show(panel.value===p?'':p).catch(e=>localError.value=e.message)}
async function example(d){
 w.loadExample({workflow:d.workflow,layout:d.layout});localError.value='';pick.value=null
 const identity=w.base
 try {
  for(const n of identity.graph.nodes){
   if(!w.catalog.nodeDefinitions.some(def=>def.typeId===n.typeId && def.version===n.typeVersion))throw Error('NODE_UNRESOLVED · '+n.typeId)
  }
  if(identity.graph.nodes.some(n=>n.typeId==='p08.lmstudio.text')){
   const bindings=await w.api('load',{action:'local-settings'}),binding=bindings['LM Studio']
   if(!binding)throw Error('LOCAL_CONNECTION_NOT_CONFIGURED')
   const ids=await w.api('load',{action:'local-list',url:binding.url})
   if(!ids.includes(binding.model))throw Error('LOCAL_MODEL_UNAVAILABLE')
  }
 }catch(e){if(w.base===identity)localError.value=String(e.message)}
}
async function run(){if(!w.canRun)return;panel.value='运行';await w.run()}
async function importDoc(e){await w.importFile(e);pick.value=null}
function finishLink(n,p){w.connect({...pick.value,target:n.id,targetHandle:p.id});pick.value=null}
watch(()=>w.error,v=>{if(v)panel.value='运行'})
const details=computed(()=>w.selected?w.ports(w.selected).filter(p=>p.id!=='error'):[])
const node=(id)=>w.nodeData(id)
function pins(id,direction){return node(id).ports.filter(p=>p.direction===direction&&p.id!=='error')}
function fresh(){
 if(!w.catalog)return
 const d=structuredClone(examples.find(item=>item.code==='WF-02').workflow)
 d.workflowId='flow-'+crypto.randomUUID().slice(0,12);d.title='未命名工作流'
 d.graph.nodes=d.graph.nodes.filter(n=>['text','output'].includes(n.id))
 d.graph.nodes[0].config.value='输入文本'
 d.graph.edges=[{id:'text-output',kind:'data',from:{node:'text',port:'out'},to:{node:'output',port:'in'},order:0}]
 d.environmentRequirements=[]
 w.loadExample({workflow:d,layout:{version:'aos-layout/0.1',positions:{text:{x:0,y:60},output:{x:540,y:60}}}})
 panel.value='组件';pick.value=null;localError.value=''
}
</script>
<template><main class="studio"><header class="app-head"><img :src="glyph('Workflow')" width="19" alt="AOS"><div class="breadcrumb"><span>AOS Studio</span><i>/</i><span class="flow-symbol">⌘</span><h1>{{w.base?.title||'工作流'}}</h1></div></header>
<div class="stage"><nav class="rail"><button v-for="[p,icon] in [['组件','Blocks'],['文件','FolderOpen'],['属性','SlidersHorizontal'],['模型','BrainCircuit'],['运行','Play']]" :key="p" :aria-label="p" :aria-pressed="panel===p" @click="toggle(p)"><img :src="glyph(icon)" alt=""></button><hr/><button aria-label="撤销" @click="w.undo"><img :src="glyph('Undo2')" alt=""></button><button aria-label="重做" @click="w.redo"><img :src="glyph('Redo2')" alt=""></button></nav>
<aside v-if="panel" class="side"><div class="library" v-if="panel==='组件'"><label class="filter"><input aria-label="搜索组件" placeholder="搜索" v-model="w.search"></label><h2>组件</h2>
<section v-for="g in w.groups" :key="g"><button class="category" @click="group=group===g?'':g">{{g}}　›</button>
<template v-if="w.search||group===g"><button class="component" v-for="[tid,label] in w.palette.filter(([t])=>w.groupOf(t)===g)" :key="tid" :data-type="tid" draggable="true" @dragstart="e=>e.dataTransfer.setData('application/aos-node',tid)" @click="w.add(tid)">{{label}}</button></template></section></div>
<div v-if="panel==='文件'" class="files"><button @click="fresh" :disabled="!ready">新建工作流</button><h2>示例</h2><button v-for="d in examples" :key="d.code" :data-example="d.code" @click="example(d)" :disabled="!ready">{{d.code}} · {{d.workflow.title}}</button>
<p v-if="localError" role="alert">{{localError}}</p><h2>工作区</h2><label>文档名称<input aria-label="文档名称" v-model="w.name" maxlength="48"></label><button @click="w.save" :disabled="!ready||w.busy">保存工作流</button><button v-for="doc in w.documents" :key="doc" @click="w.name=doc;w.open()">{{doc}}</button>
<button @click="file.click()" :disabled="!ready">导入 JSON</button><input hidden type="file" accept=".json" ref="file" @change="importDoc"><button @click="w.download" :disabled="!w.base">导出 JSON</button></div>
<div v-if="panel==='模型'" class="editor-form"><h2>本地模型</h2><select aria-label="服务" v-model="w.service" @change="w.readConnection"><option>LM Studio</option><option>Ollama</option></select><label>地址<input aria-label="地址" v-model="w.address"></label><button @click="w.listModels">测试连接</button><label>模型<select aria-label="模型 ID" v-model="w.modelId"><option v-for="m in w.available" :key="m">{{m}}</option></select></label><button :disabled="!w.modelId" @click="async()=>{await w.saveConnection();await w.refresh()}">保存连接</button><p role="status">{{w.feedback}}</p></div>
<div v-if="panel==='属性'&&w.selected" class="editor-form"><h2>{{w.labels[w.selected.typeId]||w.selected.typeId}}</h2><label v-for="[k,s] in w.fields" :key="w.selected.id+k">{{s.title||k}}
<input v-if="s.const!==undefined" :aria-label="k" :value="s.const" readonly><select v-else-if="s.enum" :aria-label="k" :value="w.selected.config[k]" @change="w.setField(k,s,$event)"><option v-for="v in s.enum" :key="v">{{v}}</option></select>
<input v-else-if="s.type==='boolean'" type="checkbox" :aria-label="k" :checked="w.selected.config[k]" @change="w.setField(k,s,$event)"><input v-else-if="['integer','number'].includes(s.type)" type="number" :aria-label="k" :value="w.selected.config[k]" :min="s.minimum" :max="s.maximum" @change="w.setField(k,s,$event)">
<textarea v-else-if="s.type==='string'" :aria-label="k" :value="w.selected.config[k]" @change="w.setField(k,s,$event)"/></label>
<button v-for="p in details" :key="p.id" :data-port="p.id" :disabled="p.direction==='input'&&!pick" @click="p.direction==='output'?pick={source:w.selected.id,sourceHandle:p.id}:finishLink(w.selected,p)">{{p.direction==='output'?'从':'连接到'}} {{p.id}} · {{p.type.schemaRef||p.type.name}}</button></div>
<div v-if="panel==='运行'" class="run-view"><h2>运行记录</h2><p v-if="w.connection!=='C1 已连接'">{{w.connection}}</p><p role="alert" v-if="w.error||localError">{{w.error||localError}}</p>
<template v-if="w.snapshot"><strong data-testid="state">{{ready?w.labelState(w.snapshot.state):'状态待核实'}}</strong><code>{{w.snapshot.runId}}</code>
<div v-for="a in w.approvals" :key="a.id"><pre>{{a.action?.inputs}}</pre><button :disabled="!ready||!a.verified||w.busy" @click="w.decide(a,true)">批准本次操作</button><button :disabled="!ready||w.busy" @click="w.decide(a,false)">拒绝</button></div>
<p v-for="e in w.problems" :key="e.id">{{e.id}} · {{e.message}}</p><pre data-testid="output">{{w.result??''}}</pre><button v-if="!w.terminal" :disabled="w.busy||!ready" @click="w.cancel">取消运行</button>
<details><summary>事件</summary><div v-for="e in w.events" :key="e.seq">{{e.seq}} · {{e.kind}} {{e.key}}</div></details></template></div>
<button class="collapse" aria-label="收起侧栏" @click="panel=''">‹</button></aside>
<section class="canvas-host" @dragover.prevent @drop="w.drop"><VueFlow v-model:nodes="w.nodes" v-model:edges="w.edges" :min-zoom=".2" :max-zoom="2" :delete-key-code="null" :zoom-on-double-click="false" :is-valid-connection="w.validConnection" @connect="w.connect" @node-double-click="panel='属性'" @node-drag-start="w.capture" @node-drag-stop="w.saved=false">
<template #node-aos="{id,selected}"><article class="flow-card" :class="{selected}" :data-node-id="id"><div class="card-name"><img :src="node(id).spec.typeId.startsWith('p08.')?glyph('BrainCircuit'):variableIcon" class="material-icon" alt=""><strong>{{node(id).label}}</strong></div><div class="card-field">{{node(id).preview||node(id).spec.config.model||node(id).spec.typeId}}</div>
<template v-for="dir in ['input','output']"><Handle v-for="(p,i) in pins(id,dir)" :key="dir+p.id" :id="p.id" :type="dir==='input'?'target':'source'" :position="dir==='input'?Position.Left:Position.Right" :style="{top:(100*(i+1)/(pins(id,dir).length+1))+'%'}"/></template>
<div v-if="node(id).state" class="node-state">{{ready?node(id).status:'待核实'}}</div></article></template><Background pattern-color="#b6b7c4" :gap="19" :size="1"/></VueFlow>
<div class="actions"><button aria-label="保存草稿" :disabled="!ready||w.busy" @click="w.save">{{w.saved?'已保存':'保存'}}</button><button :disabled="!ready||!w.base||w.busy" @click="async()=>{await w.validate();panel='运行'}">校验</button><button data-testid="run" :disabled="!w.canRun" @click="run">运行</button></div>
<div class="view-tools native-zoom"><button @click="w.zoomOut()">−</button><button @click="w.fitView({padding:.1,maxZoom:1})">适配画布</button><button @click="w.zoomIn()">+</button></div></section></div></main></template>
