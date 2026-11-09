"""Own research artifacts only: tokens, provenance, visual contact sheets and audit."""
from pathlib import Path
import hashlib,json,re
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parent;PROJECT=ROOT.parents[1]
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def write(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def font(size,bold=False):return ImageFont.truetype('C:/Windows/Fonts/msyhbd.ttc' if bold else 'C:/Windows/Fonts/msyh.ttc',size)
def contact(dest,items,header,reference=False):
    W=1920;H=1400;im=Image.new('RGB',(W,H),'#11171e');d=ImageDraw.Draw(im)
    d.text((34,25),header,font=font(30,True),fill='#e9eff6');d.text((34,75),'真实截图审查 / 仅设计研究，不是后端运行证明',font=font(17),fill='#b8c6d5')
    for i,(p,title,desc) in enumerate(items):
        x=32+(i%2)*944;y=126+(i//2)*624
        d.text((x,y),title,font=font(22,True),fill='#a9caff');d.text((x,y+37),desc,font=font(16),fill='#bdc8d3')
        pic=Image.open(p).convert('RGB');pic.thumbnail((912,540),Image.Resampling.LANCZOS)
        d.rectangle((x,y+72,x+912,y+612),fill='#1c232b',outline='#485563');im.paste(pic,(x+(912-pic.width)//2,y+72+(540-pic.height)//2))
    im.save(dest)
def ratio(a,b):
    def lum(c):
        v=[int(c[i:i+2],16)/255 for i in (1,3,5)];v=[x/12.92 if x<=.04045 else ((x+.055)/1.055)**2.4 for x in v];return sum(x*w for x,w in zip(v,(.2126,.7152,.0722)))
    x,y=sorted((lum(a),lum(b)));return (y+.05)/(x+.05)
def main():
    css=(ROOT/'boards/tokens.css').read_text(encoding='utf-8');blocks=re.findall(r'([^{}]+)\{([^{}]+)\}',css);profiles={selector.strip():dict(re.findall(r'--([\w-]+):([^;]+)',body)) for selector,body in blocks}
    tokens={'version':'0.1-design-draft','status':'proposed, not a product API','profiles':profiles,'type':{'ui':['Segoe UI Variable Text','Segoe UI','Microsoft YaHei UI'],'code':['Consolas','monospace'],'bodyPx':13,'bodyLinePx':20,'captionPx':11,'titlePx':17},'spacingPx':[2,4,8,12,16,24,32],'radiusPx':{'control':3,'node':4,'pill':2},'strokePx':{'structural':1,'selected':2,'focus':2,'wire':1.5,'wireSelected':2.5},'density':{'standard':{'control':32,'row':30,'font':13},'compact':{'control':28,'row':26,'font':12},'comfortablePlanned':{'control':36,'row':34,'font':14}},'motion':{'decorative':0,'optionalFeedbackMs':100,'reducedMotion':'no spatial animation; retain text feedback'},'note':'CSS is used by static boards; JSON extracts its current profile values. Remaining tokens are proposed component guidance.'}
    write(ROOT/'design-tokens.json',tokens)
    contrasts=[]
    for name,selector in [('A',':root'),('B','[data-direction=b]'),('C','[data-direction=c]')]:
        theme={**profiles[':root'],**profiles.get(selector,{})}
        for foreground in ('text','muted','accent','success','warning','error'):
            contrasts.append({'theme':name,'foreground':foreground,'background':'panel','ratio':round(ratio(theme[foreground],theme['panel']),2),'target':4.5})
        contrasts.append({'theme':name,'foreground':'control-border','background':'panel','ratio':round(ratio(theme['control-border'],theme['panel']),2),'target':3.0})
    write(ROOT/'evidence/contrast-check.json',{'method':'sRGB relative luminance, unblended semantic token pairs','pairs':contrasts,'note':'Does not cover all boundaries, overlays, font rendering, WCAG, color vision or reading tests.'})
    items=[(ROOT/'screenshots/a-standard.png','A / 石墨灰工作台 · 推荐','节点库 + 画布 + 300px检查器 + 完整调试区'),(ROOT/'screenshots/b-daylight.png','B / 明色参数工作台','浅色面板 + 340px检查器，便于长参数检查'),(ROOT/'screenshots/c-focus.png','C / 画布优先','折叠节点库 + 紧凑行高 + 浅调试区'),(ROOT/'screenshots/a-approval.png','A / 等待审批状态','内容与权限可检查；未批准不等于已经执行')]
    contact(ROOT/'screenshots/directions-comparison.png',items,'AOS · 桌面工作区方向对比')
    refs=[(ROOT/'references/comfy-original.png','ComfyUI / 官方工作区截图','当前文档示例；画布与右侧参数'),(ROOT/'references/blender-workspace.jpg','Blender / 官方手册仓库截图','较早Compositor示例；不是当前Geometry Nodes全窗口'),(ROOT/'references/vscode-original.png','VS Code / 官方标注截图','编辑主体、导航、Panel与Status Bar'),(ROOT/'references/unreal-lab-figure1.png','Unreal Blueprint / 大学NExT Lab截图','较早UE4真实工作区；当前语义另查Epic文档')]
    contact(ROOT/'screenshots/reference-comparison.png',refs,'真实工作区 · 视觉研究引用（版权归原作者）',True)
    manifest=[]
    urls=['https://docs.comfy.org/interface/overview','https://projects.blender.org/blender/blender-manual/media/branch/main/manual/images/interface_controls_nodes_introduction_example.jpg','https://code.visualstudio.com/docs/editing/getting-started/userinterface','https://ms-kb.msd.unimelb.edu.au/next-lab/virtual-reality/guides/vr-development-overview/unreal-engine-overview/unreal-engine-primer/interactivity-and-blueprints']
    for (p,title,desc),url in zip(refs,urls):manifest.append({'title':title,'scope':desc,'referencePage':url,'local':str(p.relative_to(ROOT)),'sha256':sha(p),'pixels':Image.open(p).size})
    manifest[-1]['imageUrl']=(ROOT/'references/unreal-lab-figure1-source.txt').read_text(encoding='utf-8')
    manifest[0]['imageUrl']=read(ROOT/'references/screenshots-provenance.json')[0]['sourceImage']
    write(ROOT/'references/final-image-provenance.json',manifest)
    baseline=read(ROOT/'evidence/baseline.json');changed=[];missing=[]
    for rel,h in baseline.items():
        p=PROJECT/rel
        if not p.exists():missing.append(rel)
        elif sha(p)!=h:changed.append(rel)
    broken=[]
    for p in ROOT.glob('*.md'):
        for target in re.findall(r'\]\(([^)]+)\)',p.read_text(encoding='utf-8')):
            if '://' not in target and not target.startswith('#') and not (p.parent/target.split('#')[0]).exists():broken.append({'file':p.name,'target':target})
    render=read(ROOT/'evidence/render-checks.json');desktop=[r for r in render['records'] if r['width']>=1024]
    badRender=[r['name'] for r in desktop if r['canvas']['width']<400 or r['canvas']['height']<200 or r['overflow'] or r['minimapOverlapsNodes'] or not r['allRunControlsDisabled']]
    approval=next(r for r in render['records'] if r['name']=='a-approval')
    discovered=read(ROOT/'evidence/after-skills.json')['result']['data'][0]
    installed=[s for s in discovered['skills'] if s['name']=='frontend-design'];skill=read(ROOT/'evidence/skill-install-manifest.json')
    output={'protectedBaselineFiles':len(baseline),'modifiedBaselineFiles':changed,'unexpectedModifications':[x for x in changed if x!='README.md'],'missingProtectedFiles':missing,'P006EngineIPCAdaptersUnchanged':not any(x.startswith('experiments/') for x in changed),
        'frontendInstalledOnce':len(installed)==1,'frontendScope':installed[0]['scope'],'frontendEnabled':installed[0]['enabled'],'nativeDiscoveryErrors':discovered.get('errors',[]),'reviewedSkillBytesPreserved':all(sha(PROJECT/'.agents/skills/frontend-design'/rel)==h for rel,h in skill['original'].items()),'optionalInstalled':(PROJECT/'.agents/skills/ui-ux-pro-max').exists(),
        'renderScreenshots':len(render['records'])+1,'consoleErrors':render['consoleErrors'],'desktopRenderErrors':badRender,'approvalButtons':approval['approvalButtonCount'],'brokenLinks':broken,'contrastTokenPairs':len(contrasts),'belowTextContrastTarget':[x for x in contrasts if x['ratio']<x['target']],
        'blenderLfsHashMatches':sha(ROOT/'references/blender-workspace.jpg')=='735585d98f5f9f6ed328e471c0e6cc41038f3b1d15cbcd3f7307b350cf0bd0f4','state':'design delivery, user direction choice pending; P0-07 not started'}
    write(ROOT/'evidence/delivery-audit.json',output)
    hashes={str(p.relative_to(ROOT)):sha(p) for p in [*ROOT.glob('*.md'),*ROOT.glob('*.py'),*ROOT.glob('*.cjs'),*ROOT.glob('boards/*'),ROOT/'design-tokens.json'] if p.is_file()};write(ROOT/'evidence/artifact-hashes.json',hashes)
    print(json.dumps(output,ensure_ascii=False));return int(bool(output['unexpectedModifications'] or missing or broken or badRender or render['consoleErrors'] or approval['approvalButtonCount']!=2 or not output['reviewedSkillBytesPreserved'] or not output['frontendInstalledOnce'] or not output['frontendEnabled'] or output['optionalInstalled'] or output['belowTextContrastTarget']))
if __name__=='__main__':raise SystemExit(main())
