import L from 'leaflet'

export const ll = (x: number, z: number) => L.latLng(-z, x)
export const xz = (p: L.LatLng): [number, number] => [Math.floor(p.lng), Math.floor(-p.lat)]

export const $ = <T extends HTMLElement = HTMLElement>(id: string) => document.getElementById(id) as T

export const num = (n: number) => (n < 0 ? '−' : '') + Math.abs(Math.round(n)).toLocaleString('en-GB')

export const esc = (s: string) =>
  s.replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]!)

export const getJSON = async <T>(url: string): Promise<T> => {
  const r = await fetch(url, { cache: 'no-cache' })
  if (!r.ok) throw new Error(`${url}: ${r.status}`)
  return r.json() as Promise<T>
}

export const store = {
  get<T>(key: string, fallback: T): T {
    try {
      const v = localStorage.getItem('atlas:' + key)
      return v === null ? fallback : (JSON.parse(v) as T)
    } catch {
      return fallback
    }
  },
  set(key: string, value: unknown) {
    try {
      localStorage.setItem('atlas:' + key, JSON.stringify(value))
    } catch {
      /* private mode: settings just don't stick */
    }
  },
}

export async function copy(text: string, button: HTMLButtonElement) {
  const label = button.textContent
  try {
    await navigator.clipboard.writeText(text)
    button.textContent = 'Copied'
  } catch {
    button.textContent = text
  }
  setTimeout(() => (button.textContent = label), 1600)
}

export function duration(s: number) {
  if (s < 60) return `${Math.max(1, Math.round(s))} s`
  const m = Math.floor(s / 60), r = Math.round(s % 60)
  return m < 60 ? `${m} min${r ? ` ${r} s` : ''}` : `${Math.floor(m / 60)} h ${m % 60} min`
}
