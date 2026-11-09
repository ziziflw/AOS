import { createApp,h } from 'vue'
import Controller from '../App.vue'
import Workbench from './Workbench.vue'
import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'
import '../../../../../apps/aos-workbench/src/shell.css'
import './style.css'
createApp({render:()=>h(Controller,{}, {default:({workbench})=>h(Workbench,{w:workbench})})}).mount('#app')
