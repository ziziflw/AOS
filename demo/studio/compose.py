from pathlib import Path
import re
D=Path(__file__).resolve().parent;f=D/'frontend/src/App.vue';s=(D.parent/'workbench/App.vue').read_text('utf8')
s=s.replace('import FlowNode',"""import StudioShell from './StudioShell.vue'
import {NConfigProvider,NInput,NInputNumber,NButton,NCheckbox,NSelect,darkTheme} from 'naive-ui'
const shell=ref(null)
const theme={common:{primaryColor:'#8ebafe',bodyColor:'#171d24',borderRadius:'3px',fontSize:'13px'}}
const validRevision=ref('')
import FlowNode""")
a=s.index('const style=computed');b=s.index('function nodeData',a);s=s[:a]+s[b:]
s=re.sub(r'async function navigate\(next,toggle=true\).*?\n',"""async function navigate(next){shell.value.show({'工作流':'files','节点库':'nodes','连接':'connections'}[next]);await action(refresh)}
""",s)
s=s.replace("left.value=true\n}", "left.value=true;shell.value.show(empty?'nodes':'files')\n}")
s=s.replace("notice.value='C1 契约校验通过", "validRevision.value=base.value.version.revision;notice.value='C1 契约校验通过").replace("pinned.value=clone(w);","validRevision.value=w.version.revision;pinned.value=clone(w);")
a=s.index('<main class="workbench"');b=s.index(' <nav class="toolbar"',a)
s=s[:a]+'''<n-config-provider :theme="darkTheme" :theme-overrides="theme" class="studio-app"><main class="studio-frame">
'''+s[b:]
a=s.index(' <div class="workspace">');editor=s[s.index('  <section class="editor"',a):s.index('  <div v-show="right" class="splitter',a)]
ins=s[s.index('  <aside class="inspector"',a):s.index('  <div v-show="bottom" class="splitter',a)].replace('v-show="right"','')
dbg=s[s.index('  <section class="debug"',a):s.index('\n </div>\n <footer',a)].replace('v-show="bottom"','')
files=s[s.index('<section class="side-content" v-else-if="area===\'工作流\'">',a):s.index('<section class="side-content" v-else>',a)].replace(' v-else-if="area===\'工作流\'"','')
con=s[s.index('<section class="side-content" v-else>',a):s.index('<input hidden type="file"',a)].replace(' v-else>', ' @vue:mounted="()=>{if(catalog)readConnection()}">')
lib=s[s.index('<div class="library-search">',a):s.index('</div></template>\n  <section class="side-content"',a)+6]
lib=lib.replace('<input aria-label="搜索节点" v-model="search" placeholder="搜索名称、用途或分类">','<n-input size="small" clearable aria-label="搜索节点" v-model:value="search" placeholder="搜索名称、用途或分类"/>').replace('<label><input type="checkbox" v-model="onlyReady">仅显示可添加节点</label>','<n-checkbox v-model:checked="onlyReady">仅显示可添加节点</n-checkbox>')
ins=ins.replace('<input v-else-if="[\'number\',\'integer\'].includes(s.type)" type="number" :value="selected.config[key]" :aria-label="key" :min="s.minimum" :max="s.maximum" :step="s.type===\'integer\'?1:.1" @change="setField(key,s,$event)">','<n-input-number v-else-if="[\'number\',\'integer\'].includes(s.type)" size="small" :value="selected.config[key]" :aria-label="key" :min="s.minimum" :max="s.maximum" :step="s.type===\'integer\'?1:.1" @update:value="v=>{capture();selected.config[key]=v;touch()}"/>')
s=s[:a]+''' <StudioShell ref="shell">
 <template #editor>'''+editor+'''</template>
 <template #files-view>'''+files+'''</template>
 <template #nodes-view><aside class="library">'''+lib+'''</aside></template>
 <template #connections-view>'''+con+'''</template>
 <template #properties>'''+ins+'''</template>
 <template #output>'''+dbg+'''</template>
 <template #status><footer class="statusbar"><span>{{connection}}</span><span>{{validRevision&&validRevision===base?.version.revision?'契约已校验':'草稿待校验'}}</span><span>{{notice}}</span><div class="spacer"/><button aria-label="切换属性检查器" @click="shell.cfg.secondarySideBar=!shell.cfg.secondarySideBar">属性</button><button aria-label="切换执行区" @click="shell.cfg.bottomPanel=!shell.cfg.bottomPanel">输出</button><span>问题 {{problems.length+(error?1:0)}}</span></footer></template></StudioShell>
 <input hidden type="file" accept=".json" ref="fileInput" @change="async e=>{await importFile(e);welcome=false}"></main></n-config-provider>
</template>
<style>.studio-app,.studio-frame{height:100vh;width:100%;display:flex;flex-direction:column;min-height:0}.studio-frame .toolbar{flex:none;height:44px}.studio-shell .editor{display:flex;flex-direction:column;position:relative;min-height:0}.studio-shell .vue-flow{flex:1;min-height:0}.slot-body .library,.slot-body .inspector,.slot-body .debug{height:100%;width:100%;overflow:auto}.slot-body .library{display:flex;flex-direction:column}.catalog-item{display:block!important;width:100%;text-align:left}.catalog-item small{display:block}.statusbar button{height:20px;font-size:11px}.studio-shell .code-layout-status{height:24px}.studio-shell .statusbar{height:100%}.welcome{position:absolute;z-index:4;top:50px;left:16px;padding:16px;background:var(--panel);border:1px solid var(--border)}.side-content{padding:12px}.side-content label,.side-content button{display:block;margin-bottom:8px;width:100%}.n-input input{border:0;height:unset;background:transparent}.studio-shell .n-checkbox input{width:auto}.library-list h3{margin:10px 6px}.library-search{flex:none}.slot-body .debug{display:flex;flex-direction:column}</style>
'''
s=s.replace("open(){return action","open(){return action").replace("e.altKey?right.value=!right.value:left.value=!left.value","e.altKey?shell.value.cfg.secondarySideBar=!shell.value.cfg.secondarySideBar:shell.value.cfg.primarySideBar=!shell.value.cfg.primarySideBar").replace("bottom.value=!bottom.value","shell.value.cfg.bottomPanel=!shell.value.cfg.bottomPanel").replace("bottom=true;tab=","shell.cfg.bottomPanel=true;tab=")
s=s.replace('class="primary" data-testid="run"', 'class="primary" data-testid="run"')
f.write_text(s,'utf8')
