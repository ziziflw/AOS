from pathlib import Path
import shutil,subprocess
D=Path(__file__).parent.resolve();S=D.parent/'experiments/p0-08';B=D/'build'
def copy(name,skip):
 shutil.copytree(S/name,B/name,dirs_exist_ok=True,ignore=shutil.ignore_patterns(*skip))
copy('frontend',[]);copy('host',['target','gen'])
p=B/'frontend/src/App.vue';s=p.read_text(encoding='utf-8')
i=s.index('const clone=')
s=s[:i]+"""const localDialog=ref(null),service=ref('Ollama'),address=ref(''),modelId=ref(''),available=ref([]),feedback=ref('')
async function readConnection(){available.value=[];feedback.value='';const settings=await api('load',{action:'local-settings'});const saved=settings[service.value];address.value=saved?.url||(service.value==='Ollama'?'http://127.0.0.1:11434/v1':'http://127.0.0.1:1234/v1');modelId.value=saved?.model||'';if(modelId.value)available.value=[modelId.value]}
async function listModels(){try{available.value=await api('load',{action:'local-list',url:address.value});modelId.value=available.value.includes(modelId.value)?modelId.value:(available.value[0]||'');feedback.value=modelId.value?'连接成功':'模型列表为空，请先在服务中加载模型'}catch(e){available.value=[];modelId.value='';feedback.value='连接失败 · '+e.message}}
async function saveConnection(){try{await api('load',{action:'local-save',service:service.value,url:address.value,model:modelId.value});feedback.value='已保存，下次运行时生效'}catch(e){feedback.value='保存失败 · '+e.message}}
"""+s[i:]
i=s.index('<div class="library-footer">')+len('<div class="library-footer">')
s=s[:i]+"""<button @click="async()=>{await readConnection();localDialog.showModal()}">本地模型连接</button><dialog ref="localDialog" style="background:#20252c;color:#eee;border:1px solid #57606a;padding:18px;width:360px"><h3>本地模型连接</h3><label>服务<select aria-label="本地服务" v-model="service" @change="readConnection"><option>Ollama</option><option>LM Studio</option></select></label><label>回环地址<input aria-label="回环地址" v-model="address"></label><button @click="listModels">测试连接并获取模型</button><label>模型<select aria-label="发现的模型" v-model="modelId"><option v-for="id in available" :value="id">{{id}}</option></select></label><button :disabled="!modelId" @click="saveConnection">保存连接</button><p role="status">{{feedback}}</p><button @click="localDialog.close()">关闭设置</button></dialog>"""+s[i:]
s=s.replace('离线 SDK 场景','模型工作流场景').replace('离线 HTTP · 自有服务，不是模型推理。','按所选模型连接执行。').replace('受限合成环境 · 不连接收费模型或真实账户','默认使用离线合成工作流').replace('sdk模型','SDK模型')
p.write_text(s.replace('P0-08','Demo v0.1.0'),encoding='utf-8')
p=B/'host/src/window.rs'
s=p.read_text(encoding='utf-8').replace('Graphite Workbench — P0-08','Graphite Workbench — Demo v0.1.0').replace('"response":reply','"ok":reply["ok"]')
p.write_text(s,encoding='utf-8')
subprocess.run(['npm.cmd','run','build'],cwd=B/'frontend',check=True)
import os
os.environ['RUSTFLAGS']='--remap-path-prefix='+str(D.parent)+'=aos-src -C debuginfo=0 -C strip=symbols'
subprocess.run(['cargo','build','--features','window','--bin','host-window','--locked','--offline'],cwd=B/'host',check=True)

