// Reader for the MXP1 pack format written by `movies export`. See the app design spec §2.1.

export interface DictColumn {
  codes: Uint8Array | Uint16Array
  values: string[]
  nullCode: number
}

export interface ListColumn {
  offsets: Uint32Array
  codes: Uint16Array
  values: string[]
}

export type RawColumn = Uint8Array | Uint16Array | Int16Array | Uint32Array | Float32Array

type ColumnType = 'u8' | 'u16' | 'i16' | 'u32' | 'f32' | 'dict' | 'list' | 'str'

interface ColumnHeader {
  name: string
  type: ColumnType
  offset: number
  length: number
  scale?: number
  null?: number
  width?: number
  values?: string[]
}

interface Header {
  rows: number
  meta: Record<string, unknown>
  columns: ColumnHeader[]
}

export interface Pack {
  rows: number
  meta: Record<string, unknown>
  num(name: string): Float64Array
  raw(name: string): RawColumn
  dict(name: string): DictColumn
  list(name: string): ListColumn
  str(name: string): (string | null)[]
}

const NUMERIC: ColumnType[] = ['u8', 'u16', 'i16', 'u32', 'f32']

export function decodePack(bytes: ArrayBuffer): Pack {
  const view = new DataView(bytes)
  if (bytes.byteLength < 8 || new TextDecoder().decode(new Uint8Array(bytes, 0, 4)) !== 'MXP1') {
    throw new Error('Not an MXP1 pack')
  }
  const headerLength = view.getUint32(4, true)
  const header = JSON.parse(
    new TextDecoder().decode(new Uint8Array(bytes, 8, headerLength)),
  ) as Header
  const dataStart = 8 + headerLength
  const rows = header.rows

  const column = (name: string, types: ColumnType[]): ColumnHeader => {
    const col = header.columns.find((c) => c.name === name)
    if (!col) throw new Error(`Unknown column ${name}`)
    if (!types.includes(col.type)) throw new Error(`Column ${name} is ${col.type}, not ${types.join('/')}`)
    return col
  }

  const rawOf = (col: ColumnHeader): RawColumn => {
    const at = dataStart + col.offset
    switch (col.type) {
      case 'u8': return new Uint8Array(bytes, at, rows)
      case 'u16': return new Uint16Array(bytes, at, rows)
      case 'i16': return new Int16Array(bytes, at, rows)
      case 'u32': return new Uint32Array(bytes, at, rows)
      default: return new Float32Array(bytes, at, rows)
    }
  }

  return {
    rows,
    meta: header.meta,
    num(name) {
      const col = column(name, NUMERIC)
      const src = rawOf(col)
      const scale = col.scale ?? 1
      const sentinel = col.null
      const out = new Float64Array(rows)
      for (let i = 0; i < rows; i++) {
        const v = src[i]
        out[i] = Number.isNaN(v) || (sentinel !== undefined && v === sentinel) ? NaN : v * scale
      }
      return out
    },
    raw(name) {
      return rawOf(column(name, NUMERIC))
    },
    dict(name) {
      const col = column(name, ['dict'])
      const at = dataStart + col.offset
      const codes = col.width === 2 ? new Uint16Array(bytes, at, rows) : new Uint8Array(bytes, at, rows)
      return { codes, values: col.values ?? [], nullCode: col.null ?? -1 }
    },
    list(name) {
      const col = column(name, ['list'])
      const at = dataStart + col.offset
      const offsets = new Uint32Array(bytes, at, rows + 1)
      const codes = new Uint16Array(bytes, at + (rows + 1) * 4, offsets[rows])
      return { offsets, codes, values: col.values ?? [] }
    },
    str(name) {
      const col = column(name, ['str'])
      const at = dataStart + col.offset
      const offsets = new Uint32Array(bytes, at, rows + 1)
      const text = new Uint8Array(bytes, at + (rows + 1) * 4, offsets[rows])
      const decoder = new TextDecoder()
      const out: (string | null)[] = new Array<string | null>(rows)
      for (let i = 0; i < rows; i++) {
        out[i] = offsets[i + 1] === offsets[i] ? null : decoder.decode(text.subarray(offsets[i], offsets[i + 1]))
      }
      return out
    },
  }
}

export async function fetchPack(url: string): Promise<Pack> {
  const res = await fetch(url)
  if (!res.ok) throw new Error(`Could not load ${url}: HTTP ${res.status}`)
  const bytes = await res.arrayBuffer()
  const head = new Uint8Array(bytes, 0, Math.min(2, bytes.byteLength))
  if (head.length === 2 && head[0] === 0x1f && head[1] === 0x8b) {
    const stream = new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip'))
    return decodePack(await new Response(stream).arrayBuffer())
  }
  return decodePack(bytes)
}
