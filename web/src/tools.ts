import L from 'leaflet'
import type { Atlas } from './atlas'
import { KINDS, shield } from './icons'
import type { Marker } from './types'
import { duration, esc, num } from './util'

/** Scale of blocks: a bar of four alternating segments, about 140px long at any zoom. */
export function scaleBar(map: L.Map, el: HTMLElement) {
  const update = () => {
    const ppb = 2 ** map.getZoom(), target = 140 / ppb, pow = 10 ** Math.floor(Math.log10(target))
    const n = [5, 2, 1].map((f) => f * pow).find((v) => v <= target) ?? pow
    el.innerHTML = `<div class="bar" style="width:${Math.round(n * ppb)}px"><i></i><i></i><i></i><i></i></div>` +
      `<div class="ticks" style="width:${Math.round(n * ppb)}px"><span>0</span><span>${num(n)}</span></div><em>Scale of blocks</em>`
  }
  map.on('zoomend', update)
  update()
}

/** Dividers: click points to measure a route and see how long the journey takes. */
export class Ruler {
  active = false
  private pts: L.LatLng[] = []
  private layer = L.layerGroup()

  constructor(private map: L.Map, private panel: HTMLElement, private changed: (on: boolean) => void) {
    this.layer.addTo(map)
    map.on('click', (e) => this.active && this.add(e.latlng))
    document.addEventListener('keydown', (e) => e.key === 'Escape' && this.active && this.toggle(false))
  }

  toggle(on = !this.active) {
    this.active = on
    this.pts = []
    this.map.getContainer().classList.toggle('measuring', on)
    this.panel.hidden = !on
    this.render()
    this.changed(on)
  }

  private add(p: L.LatLng) {
    this.pts.push(p)
    this.render()
  }

  private render() {
    this.layer.clearLayers()
    if (this.pts.length > 1) L.polyline(this.pts, { className: 'ruler', interactive: false }).addTo(this.layer)
    for (const p of this.pts) L.circleMarker(p, { radius: 3.5, className: 'ruler-pt', interactive: false }).addTo(this.layer)
    const d = this.pts.slice(1).reduce((s, p, i) => s + Math.hypot(p.lng - this.pts[i].lng, p.lat - this.pts[i].lat), 0)
    this.panel.innerHTML = this.pts.length < 2
      ? '<h2>Measure a route</h2><p>Click the map to set points along the way. Press Esc to stop.</p>'
      : `<h2>${num(d)} blocks</h2><dl><dt>Walking</dt><dd>${duration(d / 4.317)}</dd><dt>Sprinting</dt><dd>${duration(d / 5.612)}</dd>` +
        `<dt>On horseback</dt><dd>about ${duration(d / 9.5)}</dd><dt>By boat</dt><dd>about ${duration(d / 8)}</dd></dl>` +
        '<button type="button">Start again</button>'
    this.panel.querySelector('button')?.addEventListener('click', () => this.toggle(true))
  }
}

type Hit = { score: number; label: string; sub: string; icon: string; go: () => void }

/** Find structures, warps, zones and biomes by name, or jump to typed coordinates. */
export function search(atlas: Atlas, input: HTMLInputElement, list: HTMLElement, done: () => void) {
  const row = (h: Hit) => {
    const li = document.createElement('li'), b = document.createElement('button')
    b.type = 'button'
    b.innerHTML = `${h.icon}<span><b>${esc(h.label)}</b><small>${esc(h.sub)}</small></span>`
    b.onclick = () => {
      h.go()
      done()
    }
    li.append(b)
    return li
  }
  const run = () => {
    const w = atlas.world, q = input.value.trim().toLowerCase()
    list.replaceChildren()
    if (!w || !q) return
    const c = q.match(/^(-?\d+)[\s,]+(?:-?\d+[\s,]+)?(-?\d+)$/)
    if (c) {
      const [x, z] = [+c[1], +c[2]]
      list.append(row({ score: 9, label: `Go to x ${num(x)}, z ${num(z)}`, sub: 'Coordinates', icon: '<i class="dot"></i>', go: () => atlas.goto(x, z, 2) }))
      return
    }
    const has = (s?: string) => (s ? (s.toLowerCase().startsWith(q) ? 2 : s.toLowerCase().includes(q) ? 1 : 0) : 0)
    const hits: Hit[] = []
    const where = (m: Marker) => `${KINDS[m.k].one}${m.u ? ', underground' : m.o ? ', beyond the map' : ''}, x ${num(m.x)} z ${num(m.z)}`
    for (const m of w.markers) {
      const score = has(m.n) * 3 + has(KINDS[m.k].label) * 2 + has(m.p) * 0.5 - (m.u ? 0.5 : 0)
      if (score > 0) hits.push({ score, label: m.n, sub: where(m), icon: shield(m.k), go: () => atlas.places.focus(m) })
    }
    for (const z of w.zones) {
      const score = has(z.n) * 3
      if (score) hits.push({ score, label: z.n, sub: 'Safe zone', icon: '<i class="dot ward"></i>', go: () => atlas.goto(z.pts[0][0], z.pts[0][1], 0) })
    }
    const seen = new Set<string>()
    for (const l of w.labels) {
      const score = has(l.t) * 2.5
      if (score && !seen.has(l.t)) {
        seen.add(l.t)
        hits.push({ score, label: l.t, sub: 'Biome', icon: '<i class="dot"></i>', go: () => atlas.goto(l.x, l.z, -1) })
      }
    }
    hits.sort((a, b) => b.score - a.score || a.label.localeCompare(b.label))
    if (!hits.length) list.innerHTML = `<li class="none">Nothing called “${esc(input.value.trim())}” on this map.</li>`
    list.append(...hits.slice(0, 40).map(row))
  }
  input.addEventListener('input', run)
  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') list.querySelector('button')?.click()
    if (e.key === 'Escape') done()
  })
  atlas.addEventListener('world', run)
}
