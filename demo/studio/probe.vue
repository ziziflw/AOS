<script setup>
import {ref} from 'vue'
import StudioShell from './StudioShell.vue'
import {VueFlow} from '@vue-flow/core'
const shell=ref(null),nodes=ref([{id:'a',position:{x:60,y:60},data:{label:'测试节点'}}])
</script>
<template><main style="display:flex;height:100vh;flex-direction:column"><div><button @click="shell.cfg.secondarySideBar=!shell.cfg.secondarySideBar">属性</button><button @click="shell.cfg.bottomPanel=!shell.cfg.bottomPanel">输出</button></div><StudioShell ref="shell"><template #files-view>文档列表</template><template #nodes-view>节点列表</template><template #connections-view>连接配置</template><template #properties>属性内容</template><template #output>运行内容</template><template #editor><VueFlow v-model:nodes="nodes"/></template><template #status>兼容性试验</template></StudioShell></main></template>
