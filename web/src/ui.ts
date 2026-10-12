import { STYLES, type Atlas } from './atlas'
import { ICON, KINDS, rose, shield } from './icons'
import { ALL, type Toggle } from './places'
import { Ruler, scaleBar, search } from './tools'
import { $, esc, num, store } from './util'

const narrow = matchMedia('(max-width: 720px)')

export function ui(atlas: Atlas) {
  const { map, places, index } = atlas
  for (const [id, svg] of [['t-search', ICON.search], ['t-measure', ICON.measure], ['t-key', ICON.key], ['t-theme', ICON.candle]])
    $(id).innerHTML = svg
  $('rose').innerHTML = rose()
  $('rose').onclick = () => atlas.home()
  $('z-in').onclick = () => map.zoomIn()
  $('z-out').onclick = () => map.zoomOut()
  scaleBar(map, $('scale'))

  // panels: the key stays open beside search on wide screens; phones get one bottom sheet at a time
  const key = $('key'), find = $('search')
  const set = (el: HTMLElement, button: string, open: boolean) => {
    el.hidden = !open
    $(button).setAttribute('aria-expanded', String(open))
    document.body.classList.toggle('sheet-open', narrow.matches && !(key.hidden && find.hidden))
  }
  const openKey = (open: boolean) => {
    if (open && narrow.matches) set(find, 't-search', false)
    if (!narrow.matches) store.set('key', open)
    set(key, 't-key', open)
  }
  const openFind = (open: boolean) => {
    if (open && narrow.matches) set(key, 't-key', false)
    set(find, 't-search', open)
    if (open) $('q').focus()
  }
  const reset = () => {
    set(find, 't-search', false)
    set(key, 't-key', !narrow.matches && store.get('key', true))
  }
  $('t-key').onclick = () => openKey(key.hidden !== false)
  $('t-search').onclick = () => openFind(find.hidden !== false)
  narrow.addEventListener('change', reset)
  reset()

  const setTheme = (t: string) => {
    document.documentElement.dataset.theme = t
    $('t-theme').setAttribute('aria-pressed', String(t === 'dark'))
  }
  setTheme(document.documentElement.dataset.theme ?? 'light')
  $('t-theme').onclick = () => {
    const t = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark'
    setTheme(t)
    store.set('theme', t)
  }

  const ruler = new Ruler(map, $('measure'), (on) => {
    $('t-measure').setAttribute('aria-pressed', String(on))
    if (on && narrow.matches) reset()
  })
  $('t-measure').onclick = () => ruler.toggle()
  search(atlas, $<HTMLInputElement>('q'), $('results'), () => openFind(false))

  const nav = $('worlds')
  nav.hidden = index.worlds.length < 2
  nav.innerHTML = index.worlds.map((w) => `<button type="button" data-id="${esc(w.id)}">${esc(w.name)}</button>`).join('')
  nav.onclick = (e) => {
    const id = (e.target as HTMLElement).closest('button')?.dataset.id
    if (id) atlas.open(id)
  }

  const styles = $('styles')
  styles.onclick = (e) => {
    const s = (e.target as HTMLElement).closest('button')?.dataset.style
    if (s) atlas.setStyle(s)
  }
  atlas.addEventListener('style', () =>
    styles.querySelectorAll('button').forEach((b) => b.setAttribute('aria-checked', String(b.dataset.style === atlas.style))))

  const layers = $('layers')
  layers.onchange = (e) => {
    const input = e.target as HTMLInputElement
    places.toggle(input.value as Toggle, input.checked)
  }
  const sync = () => layers.querySelectorAll('input').forEach((i) => {
    const k = i.value as Toggle
    i.checked = k === 'under' || k === 'zones' || k === 'labels' ? places.show[k] : places.show.kinds.includes(k)
  })
  places.addEventListener('change', sync)

  atlas.addEventListener('world', () => {
    const w = atlas.world!
    nav.querySelectorAll('button').forEach((b) => b.setAttribute('aria-current', String(b.dataset.id === w.id)))
    const k = Math.min(2, -w.minZoom), s = w.spawn ?? [0, 0, 0]
    const tile = `${Math.floor(s[0] / 256) >> k}_${Math.floor(s[2] / 256) >> k}`
    styles.innerHTML = w.styles.map((st) =>
      `<button type="button" role="radio" data-style="${st}" aria-checked="${st === atlas.style}">` +
      `<i style="background-image:url('maps/${w.id}/tiles/${st}/${-k}/${tile}.webp?v=${w.v}')"></i>${STYLES[st] ?? st}</button>`).join('')
    const c = places.counts()
    const row = (key: Toggle, icon: string, label: string, n?: number) =>
      `<li><label><input type="checkbox" value="${key}">${icon}<span>${label}</span><small>${n === undefined ? '' : num(n)}</small></label></li>`
    layers.innerHTML = ALL.filter((k) => c[k]).map((k) => row(k, shield(k), KINDS[k].label, c[k])).join('') +
      (c.under ? row('under', '<i class="glyph under"></i>', 'Underground', c.under) : '') +
      (w.zones.length ? row('zones', '<i class="glyph ward"></i>', 'Safe zones', w.zones.length) : '') +
      (w.labels.length ? row('labels', '<i class="glyph name">Aa</i>', 'Biome names') : '')
    sync()
    const when = new Date(index.updated)
    $('survey').textContent = `Charted ${when.toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric' })} from ${num(w.chunks)} chunks.`
  })
}
