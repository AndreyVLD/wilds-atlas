import L from 'leaflet'
import { hub, KINDS, shield } from './icons'
import type { Kind, Marker, World } from './types'
import { copy, esc, ll, num, store } from './util'

export type Toggle = Kind | 'under' | 'zones' | 'labels'
export const ALL = Object.keys(KINDS) as Kind[]
const RANK = new Map(ALL.map((k, i) => [k, i]))
const SOLO = new Set<Kind>(['spawn', 'warp', 'waystone'])
const MIN_ZOOM: Partial<Record<Kind, number>> = { ruin: -1.25, dungeon: -2, illager: -2, tower: -2 }  // minor places wait for a closer look

const sentence = (rules: string[]) => rules.map((r, i) => (i ? r[0].toLowerCase() + r.slice(1) : r)).join(', ')

/** Everything drawn on top of the tiles: heraldic markers, biome names, safe zones and the portolan chart beneath. */
export class Places extends EventTarget {
  show = store.get('show', { kinds: ALL, under: false, zones: true, labels: true })
  private w?: World
  private marks = L.layerGroup()
  private names = L.layerGroup()
  private wards = L.layerGroup()
  private chart = L.layerGroup()
  private foot = L.layerGroup()

  constructor(private map: L.Map, private link: (x: number, z: number) => string) {
    super()
    for (const [pane, z] of [['chart', 150], ['wards', 350], ['names', 450]] as const) map.createPane(pane).style.zIndex = String(z)
    for (const g of [this.chart, this.wards, this.names, this.marks, this.foot]) g.addTo(map)
    map.on('moveend', () => this.draw())
    map.on('zoomend', () => this.letter())
    map.on('popupclose', () => this.foot.clearLayers())
  }

  set(w: World) {
    this.w = w
    this.drawChart()
    this.drawWards()
    this.letter()
    this.draw()
  }

  visible = (m: Marker) => this.show.kinds.includes(m.k) && (!m.u || this.show.under)

  toggle(key: Toggle, on: boolean) {
    if (key === 'under' || key === 'zones' || key === 'labels') this.show[key] = on
    else this.show.kinds = on ? [...new Set([...this.show.kinds, key])] : this.show.kinds.filter((k) => k !== key)
    store.set('show', this.show)
    if (key === 'zones') this.drawWards()
    else if (key === 'labels') this.letter()
    else this.draw()
    this.dispatchEvent(new Event('change'))
  }

  /** Markers in view; ones that would overlap fold under the most notable, sealed with a count. */
  draw() {
    this.marks.clearLayers()
    if (!this.w) return
    const z = this.map.getZoom(), view = this.map.getBounds().pad(0.3), cells = new Map<string, Marker[]>()
    for (const m of this.w.markers) {
      if (!this.visible(m) || z < (m.u ? -1.25 : MIN_ZOOM[m.k] ?? -99) || !view.contains(ll(m.x, m.z))) continue
      if (SOLO.has(m.k) || z >= 2) {
        this.pin(m)
        continue
      }
      const p = this.map.project(ll(m.x, m.z), z), key = `${Math.floor(p.x / 30)},${Math.floor(p.y / 30)}`
      cells.set(key, [...(cells.get(key) ?? []), m])
    }
    for (const g of cells.values()) (g.length === 1 ? this.pin(g[0]) : this.seal(g))
  }

  private pin(m: Marker) {
    const size: [number, number] = m.k === 'spawn' ? [30, 35] : m.u || m.o || m.k === 'ruin' ? [18, 21] : [23, 27]
    L.marker(ll(m.x + 0.5, m.z + 0.5), {
      icon: L.divIcon({ className: `pin${m.u ? ' under' : ''}${m.o ? ' beyond' : ''}`, html: shield(m.k, esc(m.n)), iconSize: size }),
      riseOnHover: true, zIndexOffset: m.k === 'spawn' ? 1000 : SOLO.has(m.k) ? 500 : 0,
    })
      .bindTooltip(esc(m.n), { direction: 'top', offset: [0, -size[1] / 2], className: 'tip' })
      .on('click', () => this.open(m))
      .addTo(this.marks)
  }

  private seal(g: Marker[]) {
    const bounds = L.latLngBounds(g.map((m) => ll(m.x, m.z)))
    const lead = g.reduce((a, b) => (RANK.get(b.k)! < RANK.get(a.k)! ? b : a))
    L.marker(bounds.getCenter(), {
      icon: L.divIcon({ className: 'pin seal', html: `${shield(lead.k)}<b>${g.length}</b>`, iconSize: [23, 27] }),
    })
      .bindTooltip(`${esc(lead.n)} and ${g.length - 1} more`, { direction: 'top', offset: [0, -14], className: 'tip' })
      .on('click', () => this.map.flyToBounds(bounds.pad(0.6), { maxZoom: this.map.getZoom() + 2, duration: 0.5 }))
      .addTo(this.marks)
  }

  open(m: Marker) {
    const k = KINDS[m.k], ys = Array.isArray(m.y) ? m.y : null, el = document.createElement('div')
    const where = m.o ? 'Just past the edge of the explored land'
      : ys ? `${m.u ? 'Underground, ' : ''}y ${num(ys[0])} to ${num(ys[1])}` : `y ${num(m.y as number)}`
    el.className = 'note'
    const kind = [k.one === m.n ? '' : k.one, m.p ?? ''].filter(Boolean).join(', ')
    el.innerHTML = `<h3>${esc(m.n)}</h3>${kind ? `<p class="kind">${esc(kind)}</p>` : ''}<p>${where}</p>` +
      (m.c ? `<p><code>${esc(m.c)}</code></p>` : '') + `<p class="xz">x ${num(Math.floor(m.x))}, z ${num(Math.floor(m.z))}</p>` +
      '<div class="act"><button type="button">Copy coordinates</button><button type="button">Copy link</button></div>'
    const [a, b] = el.querySelectorAll('button')
    a.onclick = () => copy(`${Math.floor(m.x)} ${ys ? ys[1] : Math.floor(m.y as number)} ${Math.floor(m.z)}`, a)
    b.onclick = () => copy(this.link(m.x, m.z), b)
    this.foot.clearLayers()
    if (m.b) L.rectangle(L.latLngBounds(ll(m.b[0], m.b[3] + 1), ll(m.b[2] + 1, m.b[1])), { className: 'footprint', interactive: false }).addTo(this.foot)
    L.popup({ maxWidth: 280, offset: [0, -8], className: 'note-pop' }).setLatLng(ll(m.x + 0.5, m.z + 0.5)).setContent(el).openOn(this.map)
  }

  focus(m: Marker) {
    if (!this.show.kinds.includes(m.k)) this.toggle(m.k, true)
    if (m.u && !this.show.under) this.toggle('under', true)
    this.map.flyTo(ll(m.x, m.z), Math.max(this.map.getZoom(), 1), { duration: 0.6 })
    setTimeout(() => this.open(m), 650)
  }

  counts() {
    const c: Record<string, number> = {}
    for (const m of this.w?.markers ?? []) c[m.u ? 'under' : m.k] = (c[m.u ? 'under' : m.k] ?? 0) + 1
    return c
  }

  /** Biome names, largest first, skipping any that would collide at this zoom. */
  private letter() {
    this.names.clearLayers()
    if (!this.w || !this.show.labels) return
    const z = this.map.getZoom(), placed: L.Bounds[] = []
    for (const l of this.w.labels) {
      const r = l.r * 2 ** z
      if (r < 56) continue
      const size = Math.round(Math.min(22, 13 + r / 40)), w = l.t.length * size * 0.72 + 12, h = size * 1.4
      const p = this.map.project(ll(l.x, l.z), z), box = L.bounds([p.x - w / 2, p.y - h / 2], [p.x + w / 2, p.y + h / 2])
      if (placed.some((b) => b.intersects(box))) continue
      placed.push(box)
      L.marker(ll(l.x, l.z), {
        pane: 'names', interactive: false, keyboard: false,
        icon: L.divIcon({ className: l.w ? 'name sea' : 'name', html: `<span style="font-size:${size}px">${esc(l.t)}</span>`, iconSize: [w, h] }),
      }).addTo(this.names)
    }
  }

  private drawWards() {
    this.wards.clearLayers()
    if (!this.w || !this.show.zones) return
    for (const zn of [...this.w.zones].sort((a, b) => a.p - b.p))
      L.polygon(zn.pts.map(([x, z]) => ll(x, z)), { pane: 'wards', className: 'ward' })
        .bindTooltip(`<b>${esc(zn.n)}</b>${zn.r.length ? `<br>${esc(sentence(zn.r))}` : ''}`, { sticky: true, className: 'tip' })
        .addTo(this.wards)
  }

  /** Portolan wind lines radiating from spawn and sixteen lesser roses; they only show on uncharted vellum. */
  private drawChart() {
    this.chart.clearLayers()
    const b = this.w?.bounds
    if (!b) return
    const R = Math.max(b[2] - b[0], b[3] - b[1])
    const [cx, cz] = this.w!.spawn ? [this.w!.spawn[0], this.w!.spawn[2]] : [(b[0] + b[2]) / 2, (b[1] + b[3]) / 2]
    const hubs = [[cx, cz], ...Array.from({ length: 16 }, (_, i) => [cx + 0.85 * R * Math.cos((i * Math.PI) / 8), cz + 0.85 * R * Math.sin((i * Math.PI) / 8)])]
    const winds: L.LatLng[][][] = [[], [], []]
    for (const [hx, hz] of hubs)
      for (let i = 0; i < 32; i++) {
        const a = (i * Math.PI) / 16
        winds[i % 4 === 0 ? 0 : i % 2 === 0 ? 1 : 2].push([ll(hx, hz), ll(hx + 3 * R * Math.cos(a), hz + 3 * R * Math.sin(a))])
      }
    ;['main', 'half', 'quarter'].forEach((c, i) =>
      L.polyline(winds[i], { pane: 'chart', className: `wind ${c}`, interactive: false }).addTo(this.chart))
    for (const [hx, hz] of hubs.slice(1))
      L.marker(ll(hx, hz), { pane: 'chart', interactive: false, keyboard: false, icon: L.divIcon({ className: 'hub', html: hub, iconSize: [26, 26] }) }).addTo(this.chart)
    for (const x of [b[0] - 0.42 * R, b[2] + 0.42 * R])
      L.marker(ll(x, cz), { pane: 'chart', interactive: false, keyboard: false, icon: L.divIcon({ className: 'incognita', html: 'Terra incognita', iconSize: [220, 30] }) }).addTo(this.chart)
  }
}
