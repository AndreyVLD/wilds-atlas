import L from 'leaflet'
import { Places } from './places'
import { Readout } from './readout'
import type { Index, World } from './types'
import { getJSON, ll, store } from './util'

export const STYLES: Record<string, string> = { parchment: 'Parchment', terrain: 'Terrain', biomes: 'Biomes', height: 'Elevation' }

type View = { id: string; x: number; z: number; zoom: number; style?: string }

/** Tiles exist only where land was generated; ask for nothing else. */
class Tiles extends L.TileLayer {
  constructor(private w: World, private style: string, private have: Set<string>[]) {
    super('', {
      tileSize: 256, noWrap: true, keepBuffer: 3, updateWhenZooming: false,
      minZoom: -12, maxZoom: 8, minNativeZoom: w.minZoom, maxNativeZoom: 0,
      bounds: w.bounds ? L.latLngBounds(ll(w.bounds[0], w.bounds[3]), ll(w.bounds[2], w.bounds[1])) : undefined,
    })
  }

  getTileUrl(c: L.Coords) {
    return `maps/${this.w.id}/tiles/${this.style}/${c.z}/${c.x}_${c.y}.webp?v=${this.w.v}`
  }

  protected createTile(c: L.Coords, done: L.DoneCallback) {
    if (this.have[-c.z]?.has(`${c.x}_${c.y}`)) return super.createTile(c, done)
    const el = document.createElement('div')
    queueMicrotask(() => done(undefined, el))
    return el
  }
}

export class Atlas extends EventTarget {
  readonly map: L.Map
  readonly places: Places
  readonly readout: Readout
  world?: World
  style = store.get('style', 'parchment')
  private tiles?: Tiles
  private have: Set<string>[] = []
  private want?: string

  constructor(el: HTMLElement, readonly index: Index, readout: HTMLElement) {
    super()
    this.map = L.map(el, {
      crs: L.CRS.Simple, zoomControl: false, attributionControl: false, boxZoom: false,
      zoomSnap: 0.25, zoomDelta: 0.5, wheelPxPerZoomLevel: 110, minZoom: -6, maxZoom: 4,
    })
    this.places = new Places(this.map, (x, z) => this.link({ x, z, zoom: Math.max(this.map.getZoom(), 1) }))
    this.readout = new Readout(this.map, readout)
    this.map.on('moveend', () => this.world && history.replaceState(null, '', '#' + this.hash()))
    this.map.on('zoomend', () => el.classList.toggle('crisp', this.map.getZoom() > 0.4))
    addEventListener('hashchange', () => {
      const v = this.parse(location.hash)
      if (v) this.show(v)
    })
  }

  parse(hash: string): View | null {
    const [id, x, z, zoom, style] = decodeURIComponent(hash.replace(/^#/, '')).split('/')
    if (!this.index.worlds.some((w) => w.id === id)) return null
    return { id, x: +x || 0, z: +z || 0, zoom: Number.isFinite(+zoom) && zoom !== '' ? +zoom : -1, style }
  }

  hash(v: Partial<View> = {}) {
    const c = this.map.getCenter(), [x, z] = [v.x ?? c.lng, v.z ?? -c.lat]
    return [v.id ?? this.world!.id, Math.round(x), Math.round(z), +(v.zoom ?? this.map.getZoom()).toFixed(2), v.style ?? this.style].join('/')
  }

  link(v: Partial<View> = {}) {
    return `${location.origin}${location.pathname}#${this.hash(v)}`
  }

  /** Open a world at its default view: the whole charted area. */
  async open(id: string) {
    const fit = (w: World) => w.bounds
      ? this.map.fitBounds(L.latLngBounds(ll(w.bounds[0], w.bounds[3]), ll(w.bounds[2], w.bounds[1])), { padding: [24, 24] })
      : this.map.setView(ll(0, 0), 0)
    if (id === this.world?.id) fit(this.world)
    else await this.load(id, fit)
  }

  async show(v: View) {
    const style = v.style && STYLES[v.style] ? v.style : this.style
    const go = () => this.map.setView(ll(v.x, v.z), v.zoom, { animate: false })
    if (v.id !== this.world?.id) {
      this.style = style
      return this.load(v.id, go)
    }
    if (style !== this.style) this.setStyle(style)
    go()
  }

  /** Swap in another world; `place` sets the view before anything that needs a map position is drawn. */
  private async load(id: string, place: (w: World) => void) {
    this.want = id
    const w = await getJSON<World>(`maps/${id}/world.json`)
    if (this.want !== id) return  // another world was picked meanwhile
    const z0 = w.tiles.map((t) => t.split('_').map(Number))
    this.map.closePopup()
    this.world = w
    this.have = Array.from({ length: 1 - w.minZoom }, (_, k) => new Set(z0.map(([x, y]) => `${x >> k}_${y >> k}`)))
    this.map.setMinZoom(w.minZoom - 1)
    place(w)
    this.setStyle(w.styles.includes(this.style) ? this.style : w.styles[0])
    this.places.set(w)
    this.readout.set(w)
    this.dispatchEvent(new Event('world'))
  }

  setStyle(style: string) {
    if (!this.world) return
    this.tiles?.remove()
    this.tiles = new Tiles(this.world, style, this.have).addTo(this.map)
    this.style = style
    store.set('style', style)
    history.replaceState(null, '', '#' + this.hash())
    this.dispatchEvent(new Event('style'))
  }

  goto(x: number, z: number, zoom = this.map.getZoom()) {
    this.map.flyTo(ll(x + 0.5, z + 0.5), zoom, { duration: 0.6 })
  }

  home() {
    const s = this.world?.spawn
    if (s) this.goto(s[0], s[2], Math.max(this.map.getZoom(), 0))
  }
}
