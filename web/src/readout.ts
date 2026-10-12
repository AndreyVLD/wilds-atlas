import type L from 'leaflet'
import type { World } from './types'
import { esc, num, xz } from './util'

const SIZE = 512 * 512 * 4

/** Cursor readout: x, z, height, biome and surface block, read from per-region lookup images. */
export class Readout {
  private w?: World
  private have = new Set<string>()
  private cache = new Map<string, Promise<Uint8ClampedArray | null>>()
  private seq = 0
  private frame = 0
  private next?: L.LatLng

  constructor(private map: L.Map, private el: HTMLElement) {
    map.on('mousemove', (e) => {
      this.next = e.latlng
      this.frame ||= requestAnimationFrame(() => {
        this.frame = 0
        if (this.next) this.show(this.next)
      })
    })
    map.on('click', (e) => this.show(e.latlng))
  }

  set(w: World) {
    this.w = w
    this.have = new Set(w.data)
    this.cache.clear()
    this.el.innerHTML = `<span class="what">${matchMedia('(hover: none)').matches ? 'Tap' : 'Point at'} the map for coordinates</span>`
  }

  private load(key: string) {
    let p = this.cache.get(key)
    if (!p) {
      const w = this.w!
      p = new Promise((resolve) => {
        const img = new Image()
        img.onload = () => {
          const c = document.createElement('canvas')
          c.width = 512
          c.height = 1024
          const g = c.getContext('2d', { willReadFrequently: true })!
          g.drawImage(img, 0, 0)
          resolve(g.getImageData(0, 0, 512, 1024).data)
        }
        img.onerror = () => resolve(null)
        img.src = `maps/${w.id}/data/${key}.webp?v=${w.v}`
      })
      this.cache.set(key, p)
      if (this.cache.size > 16) this.cache.delete(this.cache.keys().next().value!)
    }
    return p
  }

  async show(p: L.LatLng) {
    const w = this.w
    if (!w) return
    const [x, z] = xz(p), id = ++this.seq, key = `${x >> 9}_${z >> 9}`
    const head = (y = '') => `<span class="xyz">x <b>${num(x)}</b> z <b>${num(z)}</b>${y}</span>`
    if (!this.have.has(key)) return void (this.el.innerHTML = head() + '<span class="what">Uncharted</span>')
    if (this.map.getZoom() < -2.5) return void (this.el.innerHTML = head())
    const d = await this.load(key)
    if (id !== this.seq) return
    const i = ((z & 511) * 512 + (x & 511)) * 4
    const v1 = d ? (d[i] << 16) | (d[i + 1] << 8) | d[i + 2] : 0
    if (!v1) return void (this.el.innerHTML = head() + '<span class="what">Uncharted</span>')
    const v2 = (d![SIZE + i] << 16) | (d![SIZE + i + 1] << 8) | d![SIZE + i + 2]
    const biome = w.biomes[v1 >> 11]?.n ?? 'Unknown', depth = v2 & 255
    const block = (w.blocks[v2 >> 8] ?? 'unknown').replaceAll('_', ' ')
    this.el.innerHTML = head(` y <b>${num((v1 & 2047) + w.minY)}</b>`) +
      `<span class="what">${esc(biome)}, ${depth ? `water ${depth} deep` : esc(block)}</span>`
  }
}
