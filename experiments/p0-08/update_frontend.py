from pathlib import Path
H=Path(__file__).resolve().parent;p=H/'frontend/src/App.vue';s=p.read_text(encoding='utf-8')
s=s.replace("const approvalDetails=ref([]);", "const modelSamples=ref({}),modelChoice=ref('p08.openai.text');const approvalDetails=ref([]);")
s=s.replace('sampleDoc=h.sample;', 'modelSamples.value=h.modelSamples;sampleDoc=h.sample;')
s=s.replace("base.value.graph.nodes.push(n);nodes.value.forEach", "if(tid.startsWith('p08.')&&tid!=='p08.json-text'){n.adapter={id:'fixture.'+tid,version:'0.1.0',capabilityId:'cap.fixture.'+tid};n.serviceSlot=tid}base.value.graph.nodes.push(n);nodes.value.forEach")
old="permissions:['synthetic:tool:'+name]}))}"
new="permissions:['synthetic:tool:'+name]}));for(const n of base.value.graph.nodes.filter(n=>n.typeId.startsWith('p08.')&&n.typeId!=='p08.json-text')){if(!base.value.environmentRequirements.some(r=>r.slot===n.typeId))base.value.environmentRequirements.push({slot:n.typeId,kind:'service',required:true,adapter:clone(n.adapter),permissions:['synthetic:model-http']})}}"
assert old in s;s=s.replace(old,new)
s=s.replace('function reset(effect=false)', "function chooseModel(){capture();applyDoc(clone(modelSamples.value[modelChoice.value]));touch()}\nfunction setBudget(key,e){capture();const v=Number(e.target.value);if(key==='concurrencyLimit')base.value.executionPolicy[key]=v;else base.value.executionPolicy.budget[key]=v;touch()}\nfunction reset(effect=false)")
s=s.replace('<div class="library-footer"><label>', '<div class="library-footer"><label>离线 SDK 场景<select aria-label="SDK场景" v-model="modelChoice" @change="chooseModel"><option v-for="(doc,tid) in modelSamples" :value="tid">{{labels[tid]}}</option></select></label><label>')
s=s.replace('<h3>参数</h3>', '<h3>参数</h3><p v-if="selected.typeId.startsWith(\'p08.\')" class="muted" data-testid="model-capability">离线 HTTP · 自有服务，不是模型推理。仅显示本节点能力 Schema 支持的参数；不支持流式、工具调用及推理参数。</p>')
s=s.replace('<h3>本次运行 · 固定修订</h3>', '<h3>运行准入 · 草稿</h3><label class="schema-field">运行 Token 上限<input aria-label="runMaxTokens" type="number" :value="base.executionPolicy.budget.maxTokens" @change="setBudget(\'maxTokens\',$event)"></label><label class="schema-field">运行费用上限（合成分）<input aria-label="runMaxCostMinor" type="number" :value="base.executionPolicy.budget.maxCostMinor" @change="setBudget(\'maxCostMinor\',$event)"></label><label class="schema-field">最大并发<input aria-label="runConcurrency" type="number" min="1" max="8" :value="base.executionPolicy.concurrencyLimit" @change="setBudget(\'concurrencyLimit\',$event)"></label><h3>本次运行 · 固定修订</h3>')
s=s.replace('<pre class="result"', '<div class="run-summary" data-testid="model-usage"><span>已确认 {{snapshot.usage.spentTokens}} Token</span><span>预留 / 待核实 {{snapshot.usage.reservedTokens}} Token</span><span>合成估算 {{snapshot.modelCosts?.estimatedMinor??0}} 分 · 预留 {{snapshot.modelCosts?.reservedMinor??0}} 分</span><span>非供应商账单</span></div><pre class="result"')
s=s.replace('模型为本地模拟。MCP 使用独立 stdio 服务。','模型 SDK 连接自有离线 HTTP 服务。OpenAI / Anthropic 真实模型未配置、未授权。MCP 继续使用独立 stdio 服务。')
p.write_text(s,encoding='utf-8')
print('Updated model controls, capability guidance and actual C1 accounting projection')
