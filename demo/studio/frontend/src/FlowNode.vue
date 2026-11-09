<script setup>
import {Handle,Position} from '@vue-flow/core'
import {inject,computed} from 'vue'
defineOptions({inheritAttrs:false})
const props=defineProps(['id','selected'])
const ctx=inject('aos-graph')
const data=computed(()=>ctx.nodeData(props.id))
</script>
<template>
  <article class="graph-node" :class="[{selected},data.state]" :data-node-id="id">
    <header><span class="node-symbol">{{data.symbol}}</span><strong>{{data.label}}</strong><small>{{data.ordinal}}</small></header>
    <div class="node-kind">{{data.spec.typeId}} <span>0.1</span></div>
    <div class="port-row" v-for="p in data.ports" :key="p.id">
      <Handle :id="p.id" :type="p.direction==='input'?'target':'source'" :position="p.direction==='input'?Position.Left:Position.Right" :aria-label="`${id} ${p.id} ${p.type.name}`"/>
      <span :class="p.direction">{{p.id}} <small>{{p.type.schemaRef||p.type.name}}</small></span>
    </div>
    <div class="node-preview">{{data.preview}}</div>
    <footer :data-state="data.state"><span>{{data.status}}</span><span v-if="data.edited">快照</span><span v-else>{{data.badge}}</span></footer>
  </article>
</template>
