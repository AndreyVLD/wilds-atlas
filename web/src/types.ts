export type Kind =
  | 'spawn' | 'warp' | 'waystone'
  | 'village' | 'tavern' | 'castle' | 'illager' | 'tower' | 'temple' | 'dungeon' | 'ruin'

export interface Marker {
  k: Kind
  n: string
  x: number
  z: number
  y: number | [number, number]
  p?: string                                // datapack
  b?: [number, number, number, number]      // footprint x0 z0 x1 z1
  s?: number                                // pieces
  u?: 1                                     // underground
  o?: 1                                     // just beyond the generated land
  c?: string                                // command, e.g. /warp wilds
}

export interface Zone { id: string; n: string; pts: [number, number][]; r: string[]; p: number }
export interface Label { t: string; x: number; z: number; r: number; w?: 1 }

export interface World {
  id: string
  name: string
  minY: number
  sea: number
  minZoom: number
  v: number
  spawn: [number, number, number] | null
  bounds: [number, number, number, number] | null
  tiles: string[]
  data: string[]
  styles: string[]
  biomes: { n: string; c: string }[]
  blocks: string[]
  markers: Marker[]
  zones: Zone[]
  labels: Label[]
  chunks: number
}

export interface Index { title: string; subtitle: string; updated: string; worlds: { id: string; name: string; v: number; chunks: number }[] }
