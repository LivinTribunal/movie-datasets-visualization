import { afterEach, describe, expect, it, vi } from 'vitest'
import { decodePack, fetchPack } from './pack'

type Col = { name: string; type: string; bytes: Uint8Array; extra?: Record<string, unknown> }

const bytesOf = (ta: ArrayBufferView) => new Uint8Array(ta.buffer, ta.byteOffset, ta.byteLength)
const gzip = async (b: Uint8Array) =>
  new Uint8Array(await new Response(new Blob([b as BlobPart]).stream().pipeThrough(new CompressionStream('gzip'))).arrayBuffer())
const pad8 = (n: number) => (8 - (n % 8)) % 8

/** Builds an inflated MXP1 buffer per spec §2.1. `gap` extra bytes sit before the first column. */
function build(rows: number, cols: Col[], meta: Record<string, unknown> = {}, gap = 0): ArrayBuffer {
  let offset = gap
  const headers = cols.map((c) => {
    const h = { name: c.name, type: c.type, offset, length: c.bytes.length, ...c.extra }
    offset += c.bytes.length + pad8(c.bytes.length)
    return h
  })
  let json = JSON.stringify({ rows, meta, columns: headers })
  const enc = new TextEncoder()
  let hLen = enc.encode(json).length
  hLen += pad8(8 + hLen)
  json = json.padEnd(hLen, ' ') // ASCII only in the header, so chars = bytes
  const out = new Uint8Array(8 + hLen + offset)
  out.set(enc.encode('MXP1'), 0)
  new DataView(out.buffer).setUint32(4, hLen, true)
  out.set(enc.encode(json), 8)
  cols.forEach((c, i) => out.set(c.bytes, 8 + hLen + headers[i].offset))
  return out.buffer
}

const strCol = (name: string, items: string[]): Col => {
  const enc = new TextEncoder()
  const parts = items.map((s) => enc.encode(s))
  const offsets = new Uint32Array(items.length + 1)
  parts.forEach((p, i) => { offsets[i + 1] = offsets[i] + p.length })
  const bytes = new Uint8Array(offsets.byteLength + offsets[items.length])
  bytes.set(bytesOf(offsets), 0)
  parts.forEach((p, i) => bytes.set(p, offsets.byteLength + offsets[i]))
  return { name, type: 'str', bytes }
}

describe('decodePack', () => {
  it('decodes numeric types with scale and null', () => {
    const buf = build(3, [
      { name: 'a', type: 'u16', bytes: bytesOf(new Uint16Array([775, 65535, 0])), extra: { scale: 0.1, null: 65535 } },
      { name: 'b', type: 'i16', bytes: bytesOf(new Int16Array([-50, -32768, 20])), extra: { scale: 0.1, null: -32768 } },
      { name: 'c', type: 'f32', bytes: bytesOf(new Float32Array([1.5, NaN, 2])) },
      { name: 'd', type: 'u8', bytes: new Uint8Array([1, 2, 255]), extra: { null: 255 } },
      { name: 'e', type: 'u32', bytes: bytesOf(new Uint32Array([7, 0, 9])), extra: { null: 0 } },
    ], { k: 1 })
    const p = decodePack(buf)
    expect(p.rows).toBe(3)
    expect(p.meta).toEqual({ k: 1 })
    expect(Array.from(p.num('a')).map((v) => (Number.isNaN(v) ? null : Number(v.toFixed(1))))).toEqual([77.5, null, 0])
    expect(Array.from(p.num('b')).map((v) => (Number.isNaN(v) ? null : Number(v.toFixed(1))))).toEqual([-5, null, 2])
    expect(Array.from(p.num('c')).map((v) => (Number.isNaN(v) ? null : v))).toEqual([1.5, null, 2])
    expect(Array.from(p.num('d')).map((v) => (Number.isNaN(v) ? null : v))).toEqual([1, 2, null])
    expect(Array.from(p.num('e')).map((v) => (Number.isNaN(v) ? null : v))).toEqual([7, null, 9])
  })

  it('raw returns exact integers above 2^24', () => {
    const big = 2 ** 24 + 1
    const p = decodePack(build(2, [{ name: 'id', type: 'u32', bytes: bytesOf(new Uint32Array([big, 4294967295])) }]))
    const raw = p.raw('id')
    expect(raw).toBeInstanceOf(Uint32Array)
    expect(Array.from(raw)).toEqual([big, 4294967295])
  })

  it('throws on an unknown column or a wrong type', () => {
    const p = decodePack(build(1, [{ name: 'a', type: 'u8', bytes: new Uint8Array([1]) }]))
    expect(() => p.num('nope')).toThrow('Unknown column nope')
    expect(() => p.dict('a')).toThrow()
    expect(() => p.str('a')).toThrow()
  })

  it('decodes dict columns', () => {
    const p = decodePack(build(3, [
      { name: 's', type: 'dict', bytes: new Uint8Array([0, 1, 255]), extra: { width: 1, values: ['x', 'y'], null: 255 } },
      { name: 'w', type: 'dict', bytes: bytesOf(new Uint16Array([2, 0, 1])), extra: { width: 2, values: ['p', 'q', 'r'], null: 65535 } },
    ]))
    const s = p.dict('s')
    expect(Array.from(s.codes)).toEqual([0, 1, 255])
    expect(s.values).toEqual(['x', 'y'])
    expect(s.nullCode).toBe(255)
    expect(Array.from(p.dict('w').codes)).toEqual([2, 0, 1])
  })

  it('decodes list columns including an empty list', () => {
    const offsets = new Uint32Array([0, 2, 2, 3])
    const codes = new Uint16Array([0, 1, 1])
    const bytes = new Uint8Array(offsets.byteLength + codes.byteLength)
    bytes.set(bytesOf(offsets), 0)
    bytes.set(bytesOf(codes), offsets.byteLength)
    const p = decodePack(build(3, [{ name: 'c', type: 'list', bytes, extra: { values: ['US', 'FR'] } }]))
    const l = p.list('c')
    expect(Array.from(l.offsets)).toEqual([0, 2, 2, 3])
    expect(Array.from(l.codes)).toEqual([0, 1, 1])
    expect(l.values).toEqual(['US', 'FR'])
  })

  it('decodes str columns with null and non-ASCII', () => {
    const p = decodePack(build(3, [strCol('t', ['Amélie', '', '千と千尋'])]))
    expect(p.str('t')).toEqual(['Amélie', null, '千と千尋'])
  })

  it('decodes a column whose offset is 8 inside the data section', () => {
    const p = decodePack(build(2, [{ name: 'a', type: 'u32', bytes: bytesOf(new Uint32Array([5, 6])) }], {}, 8))
    expect(Array.from(p.raw('a'))).toEqual([5, 6])
  })

  it('throws on bad magic', () => {
    const buf = build(1, [{ name: 'a', type: 'u8', bytes: new Uint8Array([1]) }])
    new Uint8Array(buf)[0] = 0x58
    expect(() => decodePack(buf)).toThrow('Not an MXP1 pack')
  })
})

describe('fetchPack', () => {
  afterEach(() => vi.unstubAllGlobals())
  const plain = () => build(2, [{ name: 'a', type: 'u8', bytes: new Uint8Array([3, 4]) }])
  const respond = (body: Uint8Array) =>
    vi.stubGlobal('fetch', vi.fn(async () => new Response(body as BodyInit)))

  it('inflates a gzipped pack', async () => {
    respond(await gzip(new Uint8Array(plain())))
    expect(Array.from((await fetchPack('data/x.pack')).raw('a'))).toEqual([3, 4])
  })

  it('accepts a plain pack', async () => {
    respond(new Uint8Array(plain()))
    expect(Array.from((await fetchPack('data/x.pack')).raw('a'))).toEqual([3, 4])
  })

  it('throws on a bad response', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response('', { status: 404 })))
    await expect(fetchPack('data/x.pack')).rejects.toThrow('Could not load data/x.pack: HTTP 404')
  })
})
