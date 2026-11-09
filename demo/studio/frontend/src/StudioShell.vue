<script setup>
import {h,onMounted,onBeforeUnmount,reactive,ref,watch} from 'vue'
import {CodeLayout,CodeLayoutRootGrid,defaultCodeLayoutConfig} from 'vue-code-layout'
import 'vue-code-layout/lib/vue-code-layout.css'
const emit=defineEmits(['activate'])
const tree=ref(new CodeLayoutRootGrid());const layout=ref(null),key='aos-code-layout-v1'
const cfg=reactive({...defaultCodeLayoutConfig,titleBar:false,menuBar:false,primarySideBarWidth:19,secondarySideBarWidth:22,bottomPanelHeight:22,secondarySideBar:true,secondaryActivityBarPosition:'hidden',primarySideBarMinWidth:180,secondarySideBarMinWidth:220})
try{Object.assign(cfg,JSON.parse(localStorage.getItem(key))?.config||{})}catch{}
const labels={files:'工作流',nodes:'节点库',connections:'连接',properties:'属性',output:'运行'}
const glyph={files:'▤',nodes:'⊞',connections:'⇄'}
function icon(name){return ()=>h('span',{'aria-label':labels[name],title:labels[name],class:'aos-activity-icon'},glyph[name]||'·')}
function show(name){cfg.primarySideBar=true;layout.value.getPanelByName(name)?.activeSelf();emit('activate',name)}
function save(){if(layout.value)localStorage.setItem(key,JSON.stringify({tree:layout.value.saveLayout(),config:Object.fromEntries(['primarySideBarWidth','secondarySideBarWidth','bottomPanelHeight','primarySideBar','secondarySideBar','bottomPanel'].map(k=>[k,cfg[k]]))}))}
onMounted(()=>{
 let stored;try{stored=JSON.parse(localStorage.getItem(key))}catch{}
 if(stored?.tree){try{layout.value.loadLayout(stored.tree,p=>({...p,iconLarge:icon(p.name)}));Object.assign(cfg,stored.config);return}catch{layout.value.clearLayout()}}
 for(const name of ['files','nodes','connections']){
 const g=layout.value.addGroup({name,title:labels[name],tooltip:labels[name],iconLarge:icon(name)},'primarySideBar')
 g.addPanel({name:name+'-view',title:labels[name],startOpen:true})
 }
 for(const [name,part] of [['properties','secondarySideBar'],['output','bottomPanel']])layout.value.getRootGrid(part).addPanel({name,title:labels[name],startOpen:true})
 show('files')
})
window.addEventListener('beforeunload',save);window.addEventListener('pointerup',save);onBeforeUnmount(()=>{save();window.removeEventListener('beforeunload',save);window.removeEventListener('pointerup',save)})
defineExpose({show,cfg,save})
</script>
<template><div class="studio-shell"><CodeLayout ref="layout" v-model:layoutData="tree" :layout-config="cfg" :lang-config="{lang:'zh'}"><template #activityBarTopMenuBar></template><template #activityBarSecondaryTopMenuBar></template><template #centerArea><slot name="editor"/></template><template #panelRender="{panel}"><div class="slot-body"><slot :name="panel.name"/></div></template><template #statusBar><slot name="status"/></template></CodeLayout></div></template>
<style>.studio-shell{position:relative;flex:1;min-height:0;width:100%;overflow:hidden}.slot-body{height:100%;overflow:auto}.aos-activity-icon{font:22px/1.2 sans-serif}.studio-shell .editor{height:100%;width:100%}</style>


