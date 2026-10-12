import type { Kind } from './types'

const star = (cx: number, cy: number, R: number, r: number, n: number) =>
  'M' + Array.from({ length: 2 * n }, (_, i) => {
    const a = (Math.PI * i) / n - Math.PI / 2, d = i % 2 ? r : R
    return `${(cx + d * Math.cos(a)).toFixed(2)} ${(cy + d * Math.sin(a)).toFixed(2)}`
  }).join('L') + 'z'

// Heraldic charges, drawn on a 24×28 shield.
const CHARGE = {
  banner: 'M7.8 5.5h1.6V20H7.8zM9.4 6.3h8.8l-2.4 3.2 2.4 3.2H9.4z',
  star: star(12, 12.6, 7, 2.6, 8),
  stone: 'M9 19.5l.7-11.5L12 5.5 14.3 8l.7 11.5zM11.4 10h1.2v6.5h-1.2z',
  house: 'M12 6.5 18 12v7.5H6V12zM10.5 19.5v-4h3v4z',
  tankard: 'M7.5 9h7.5v10.5H7.5zM15 11h1.8a1.7 1.7 0 0 1 1.7 1.7v2.6a1.7 1.7 0 0 1-1.7 1.7H15v-1.6h1.6v-2.8H15zM7 9c.5-1.7 2-2.1 3.2-1.3.9-1.2 2.7-1.3 3.7-.2 1-.5 1.9.2 2 1.5z',
  castle: 'M6 19.5V9.5h2.5v2h2v-2h3v2h2v-2H18v10h-4v-3a2 2 0 0 0-4 0v3z',
  temple: 'M5.5 10.5 12 6.5l6.5 4zM7 11.5h2V18H7zM11 11.5h2V18h-2zM15 11.5h2V18h-2zM5.5 18.5h13V20h-13z',
  tower: 'M9.5 11h5v8.5h-5zM8.5 11 12 5l3.5 6zM11.3 13h1.4v2.2h-1.4z',
  axe: 'M11.2 7h1.6v12.5h-1.6zM12.8 7.5c3.4.3 5.2 2.1 5.2 4.5s-1.8 4.2-5.2 4.5z',
  skull: 'M12 6.5a5.5 5.5 0 0 0-5.5 5.5c0 2.1 1 3.4 2.4 4.1v2.9h6.2v-2.9c1.4-.7 2.4-2 2.4-4.1A5.5 5.5 0 0 0 12 6.5zM9.7 11a1.4 1.4 0 1 0 0 2.8 1.4 1.4 0 0 0 0-2.8zm4.6 0a1.4 1.4 0 1 0 0 2.8 1.4 1.4 0 0 0 0-2.8zM11.4 17h1.2v2h-1.2z',
  ruin: 'M7 19.5V11h2.6v8.5zM14.4 19.5v-5.2H17v5.2zM6.2 8.6h7.6l-1.6 1.6H6.2zM15.2 12.8l1.6-1.2 1 1.4z',
}

const ARGENT = '#f3ead2', SABLE = '#2e2418', OR = '#d9b45a'
export const KINDS: Record<Kind, { label: string; one: string; field: string; ink: string; charge: string }> = {
  spawn: { label: 'Spawn', one: 'Spawn', field: '#a8321e', ink: OR, charge: CHARGE.banner },
  warp: { label: 'Warps', one: 'Warp', field: '#24407a', ink: ARGENT, charge: CHARGE.star },
  waystone: { label: 'Waystones', one: 'Waystone', field: '#4f7d9c', ink: ARGENT, charge: CHARGE.stone },
  village: { label: 'Villages', one: 'Village', field: '#3e6b4f', ink: ARGENT, charge: CHARGE.house },
  tavern: { label: 'Taverns', one: 'Tavern', field: '#a35a26', ink: ARGENT, charge: CHARGE.tankard },
  castle: { label: 'Castles and keeps', one: 'Keep', field: SABLE, ink: OR, charge: CHARGE.castle },
  temple: { label: 'Temples and shrines', one: 'Shrine', field: '#b8902f', ink: SABLE, charge: CHARGE.temple },
  tower: { label: 'Towers', one: 'Tower', field: '#6b3f7a', ink: ARGENT, charge: CHARGE.tower },
  illager: { label: 'Illager camps', one: 'Illager camp', field: '#5f5d58', ink: ARGENT, charge: CHARGE.axe },
  dungeon: { label: 'Dungeons', one: 'Dungeon', field: '#6e2433', ink: ARGENT, charge: CHARGE.skull },
  ruin: { label: 'Ruins and landmarks', one: 'Ruin', field: '#b9ae94', ink: SABLE, charge: CHARGE.ruin },
}

const SHIELD = 'M2.5 2.5h19v10c0 6.8-4.6 11.2-9.5 13.6C7.1 23.7 2.5 19.3 2.5 12.5z'
export const shield = (k: Kind, label = '') => {
  const c = KINDS[k]
  return `<svg viewBox="0 0 24 28" ${label ? `role="img" aria-label="${label}"` : 'aria-hidden="true"'}>` +
    `<path d="${SHIELD}" fill="${c.field}"/><path d="${c.charge}" fill="${c.ink}" fill-rule="evenodd"/>` +
    `<path class="edge" d="${SHIELD}" fill="none"/></svg>`
}

/** The wind rose: sixteen points, shaded halves, a rubricated north. */
export const rose = () => {
  const point = (a: number, len: number, w: number, dark: string, light: string) =>
    `<g transform="rotate(${a})"><path class="${dark}" d="M0 0L${-w} ${-w}L0 ${-len}z"/><path class="${light}" d="M0 0L${w} ${-w}L0 ${-len}z"/></g>`
  let p = ''
  for (let i = 1; i < 16; i += 2) p += point(i * 22.5, 25, 2.6, 'g', 'l')
  for (let i = 0; i < 4; i++) p += point(45 + i * 90, 33, 5, 'd', 'g')
  for (let i = 0; i < 4; i++) p += point(i * 90, 44, 7, 'd', 'l')
  return `<svg viewBox="-50 -54 100 104" aria-hidden="true"><circle class="ring" r="30"/><circle class="ring" r="27"/>` +
    `${p}<circle class="g" r="3"/><text class="n" y="-43" text-anchor="middle">N</text></svg>`
}

export const hub = `<svg viewBox="-12 -12 24 24" aria-hidden="true"><path d="${star(0, 0, 11, 2.4, 8)}"/><circle r="2"/></svg>`

const icon = (body: string) =>
  `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${body}</svg>`
export const ICON = {
  search: icon('<circle cx="10.5" cy="10.5" r="5.5"/><path d="M14.6 14.6 20 20"/>'),
  measure: icon('<path d="M12 2.5v2"/><circle cx="12" cy="6.3" r="1.8"/><path d="M11 7.9 6.5 20.5M13 7.9l4.5 12.6M6.5 20.5l-.4 1M17.5 20.5l.4 1"/>'),
  key: icon('<path d="M12 6.6C10 5.3 7.4 4.8 4 5.1v13c3.4-.3 6 .2 8 1.5 2-1.3 4.6-1.8 8-1.5v-13c-3.4-.3-6 .2-8 1.5zM12 6.6v13"/>'),
  candle: icon('<path d="M9 11h6v8.5H9zM6 20h12M12 11V9.4"/><path d="M12 2.8c1.8 2 2.4 3.3 1.9 4.6-.3.9-1 1.5-1.9 1.5s-1.6-.6-1.9-1.5c-.5-1.3.1-2.6 1.9-4.6z" fill="currentColor"/>'),
  close: icon('<path d="M6.5 6.5l11 11M17.5 6.5l-11 11"/>'),
}
