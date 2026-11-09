import { forwardRef, useCallback, useEffect, useImperativeHandle, useRef, useState } from 'react'
import { DockviewReact, themeDark } from 'dockview-react'
import type { DockviewApi, DockviewReadyEvent, IDockviewPanelHeaderProps, SerializedDockview } from 'dockview-react'
import { Blocks, SlidersHorizontal, Workflow, X, PanelsTopLeft } from 'lucide-react'
import { Canvas, Catalog, Inspector } from '../graph'
import 'dockview-react/dist/styles/dockview.css'
import './workspace.css'

export const panelTitles = { canvas: '工作流画布', catalog: '组件目录', inspector: '属性检查器' } as const
export type PanelId = keyof typeof panelTitles
export type PresetName = '编排' | '调试' | '配置'
export interface WorkspaceState {
  preset: PresetName
  dirty: boolean
  message: string
  openPanels: PanelId[]
}
export interface WorkspaceHandle {
  open: (id: PanelId) => void
  setPreset: (name: PresetName) => void
  save: () => void
  reset: () => void
}

const panels = { canvas: () => <Canvas/>,  catalog: Catalog, inspector: Inspector }
const icons = { canvas: Workflow, catalog: Blocks, inspector: SlidersHorizontal }
export const layoutKey = 'aos.workbench.preview.layout'
const presets: PresetName[] = ['编排', '调试', '配置']
const isPanelId = (id: string): id is PanelId => Object.hasOwn(panelTitles, id)

function Tab({ api }: IDockviewPanelHeaderProps) {
  const id = api.id as PanelId
  const Icon = icons[id]
  return <div className="aos-dock-tab" data-panel-tab={id} title={panelTitles[id]}>
    <Icon size={15} strokeWidth={1.65} aria-hidden />
    <span>{panelTitles[id]}</span>
    <button type="button" className="aos-tab-close" aria-label={'关闭' + panelTitles[id]} title={'关闭' + panelTitles[id]}
      onPointerDown={e => e.stopPropagation()} onMouseDown={e => e.stopPropagation()}
      onClick={e => { e.stopPropagation(); api.close() }}><X size={13} aria-hidden /></button>
  </div>
}

const tabs = {workspaceTab: Tab}

function EmptyWorkspace() {
  return <div className="aos-dock-empty"><PanelsTopLeft size={27} aria-hidden />
    <strong>工作区没有打开的面板</strong><span>从「窗口」菜单重新打开画布、目录或检查器。</span></div>
}

type Envelope = { schemaVersion: 1; preset: PresetName; dockview: SerializedDockview }
function decodeLayout(raw: string): Envelope {
  if (raw.length > 64_000) throw new Error('layout size')
  const data: Envelope = JSON.parse(raw)
  const dock = data?.dockview
  if (data?.schemaVersion !== 1 || !presets.includes(data.preset) || !dock?.grid || !dock.panels ||
      dock.popoutGroups?.length || dock.floatingGroups?.length || dock.edgeGroups) throw new Error('layout schema')
  // Only our three docked view identities may be restored. No panel parameters or external windows.
  const ids = Object.keys(dock.panels)
  for (const id of ids) {
    const panel = dock.panels[id]
    if (!isPanelId(id) || panel?.id !== id || panel.contentComponent !== id || panel.tabComponent !== 'workspaceTab' ||
        (panel.params && Object.keys(panel.params).length > 0)) throw new Error('panel identity')
  }
  const used = new Set<string>()
  type GridNode = SerializedDockview['grid']['root']
  const visit = (node: GridNode, depth: number) => {
    if (depth > 6 || !node || (node.size !== undefined && (!Number.isFinite(node.size) || node.size < 0))) throw new Error('grid node')
    if (node.type === 'branch' && Array.isArray(node.data) && node.data.length <= 3) {
      node.data.forEach(child => visit(child, depth + 1))
      return
    }
    const group = node.data
    if (node.type !== 'leaf' || Array.isArray(group) || !Array.isArray(group?.views) ||
        (group.activeView && !group.views.includes(group.activeView))) throw new Error('grid group')
    for (const id of group.views) {
      if (!ids.includes(id) || used.has(id)) throw new Error('grid repeated panel')
      used.add(id)
    }
  }
  visit(dock.grid.root, 0)
  if (ids.length !== used.size) throw new Error('missing panel')
  return data
}

function addView(api: DockviewApi, id: PanelId, position?: {referencePanel: string; direction: 'left'|'right'|'below'|'within'}, initialSize?: number) {
  return api.addPanel({ id, component: id, title: panelTitles[id], tabComponent: 'workspaceTab', position,
    initialWidth: position?.direction === 'below' ? undefined : initialSize,
    initialHeight: position?.direction === 'below' ? initialSize : undefined,
    minimumWidth: id === 'canvas' ? 220 : 160, minimumHeight: 110 })
}

function arrange(api: DockviewApi, preset: PresetName) {
  api.clear()
  const canvas = addView(api, 'canvas')
  const place = (id: PanelId, side: 'left'|'right'|'below'|'within', size?: number, referencePanel = 'canvas') =>
    addView(api, id, { referencePanel, direction: side }, size)
  if (api.width > 0 && api.width < 700) {
    place('catalog', 'within')
    place('inspector', 'within')
    if (preset === '配置') api.getPanel('inspector')?.api.setActive()
    else canvas.api.setActive()
    return
  }
  if (preset === '调试') {
    place('inspector', 'below', Math.min(230, api.height * .38))
  } else if (preset === '配置') {
    place('inspector', 'right', Math.min(350, api.width * .39))
    place('catalog', 'within', undefined, 'inspector')
    api.getPanel('inspector')?.api.setActive()
    return
  } else {
    place('catalog', 'left', Math.min(232, api.width * .20))
    place('inspector', 'right', Math.min(264, api.width * .22))
  }
  canvas.api.setActive()
}

const initial: WorkspaceState = { preset: '编排', dirty: false, message: '', openPanels: ['canvas','catalog','inspector'] }

export const Workspace = forwardRef<WorkspaceHandle, {onState: (state: WorkspaceState) => void}>(function Workspace({onState}, ref) {
  const apiRef = useRef<DockviewApi | null>(null)
  const savedLayout = useRef('')
  const state = useRef(initial)
  const event = useRef(onState)
  event.current = onState
  const disposers = useRef<Array<{dispose(): void}>>([])
  const [pending, setPending] = useState<{preset: PresetName; reset: boolean} | null>(null)
  const dialog = useRef<HTMLDialogElement>(null)
  const publish = useCallback((changes: Partial<WorkspaceState>) => {
    state.current = {...state.current, ...changes, openPanels: apiRef.current?.panels.map(p => p.id).filter(isPanelId) || []}
    event.current(state.current)
  }, [])
  const apply = (preset: PresetName) => {
    const api = apiRef.current
    if (!api) return
    arrange(api, preset)
    publish({preset, dirty: true, message: '已应用' + preset + '布局'})
  }
  useImperativeHandle(ref, () => ({
    open(id) {
      const api = apiRef.current
      if (!api || !isPanelId(id)) return
      let panel = api.getPanel(id)
      if (!panel) {
        const anchor = api.getPanel('canvas') ?? api.activePanel
        const narrow = api.width > 0 && api.width < 700
        panel = addView(api, id, anchor ? {referencePanel: anchor.id,
          direction: narrow ? 'within' : id === 'catalog' ? 'left' : 'right'} : undefined,
          id === 'canvas' ? undefined : id === 'catalog' ? 232 : 264)
      }
      panel.api.setActive()
      api.focus()
      publish({message: '已打开' + panelTitles[id]})
    },
    setPreset(preset) {
      if (!presets.includes(preset) || preset === state.current.preset) return
      if (state.current.dirty) setPending({preset, reset:false})
      else apply(preset)
    },
    reset() { setPending({preset: state.current.preset, reset:true}) },
    save() {
      const api = apiRef.current
      if (!api) return
      const dockview = api.toJSON()
      try {
        localStorage.setItem(layoutKey, JSON.stringify({schemaVersion:1, preset:state.current.preset, dockview}))
        savedLayout.current = JSON.stringify(dockview)
        publish({dirty:false, message:'布局已保存到本机'})
      } catch {
        publish({message:'无法保存布局，请检查本地存储空间。'})
      }
    }
  }))

  const ready = ({api}: DockviewReadyEvent) => {
    disposers.current.forEach(d => d.dispose())
    apiRef.current = api
    let preset: PresetName = '编排'
    let message = ''
    try {
      const raw = localStorage.getItem(layoutKey)
      if (raw) {
        const saved = decodeLayout(raw)
        api.fromJSON(saved.dockview)
        preset = saved.preset
        message = '已恢复保存的布局'
      } else arrange(api, preset)
    } catch {
      arrange(api, preset)
      message = '布局无法读取，已恢复编排预设。'
    }
    savedLayout.current = JSON.stringify(api.toJSON())
    publish({preset, message, dirty:false})
    disposers.current = [api.onDidLayoutChange(e => {
      if (api !== apiRef.current) return
      if (!e.reasons.has('structure') && !e.reasons.has('geometry')) return
      if (JSON.stringify(api.toJSON()) !== savedLayout.current) publish({dirty:true})
    })]
  }
  useEffect(() => () => {
    disposers.current.forEach(d => d.dispose())
    apiRef.current = null
  }, [])
  useEffect(() => {
    if (pending && !dialog.current?.open) dialog.current?.showModal()
  }, [pending])
  return <div className="aos-workspace" data-testid="workspace">
    <DockviewReact components={panels} onReady={ready} theme={themeDark} tabComponents={tabs}
      watermarkComponent={EmptyWorkspace} singleTabMode="default" disableFloatingGroups />
    {pending && <dialog ref={dialog} className="aos-layout-dialog" aria-labelledby="layout-dialog-title" onCancel={()=>setPending(null)}>
      <h2 id="layout-dialog-title">{pending.reset ? '恢复默认布局？' : '切换工作区？'}</h2>
      <p>{pending.reset ? '将恢复当前预设的面板位置和尺寸。' : '当前面板布局尚未保存，切换后将应用新的预设。'}</p>
      <div><button autoFocus onClick={()=>setPending(null)}>取消</button>
        <button className="confirm" onClick={()=>{ apply(pending.preset); setPending(null) }}>{pending.reset ? '恢复默认布局' : '切换预设'}</button></div>
    </dialog>}
  </div>
})
