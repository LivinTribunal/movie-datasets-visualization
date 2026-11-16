import { readdirSync, readFileSync, existsSync, statSync } from 'node:fs'
import { gzipSync } from 'node:zlib'
import { join } from 'node:path'

const dist = new URL('../dist', import.meta.url).pathname

if (!existsSync(dist)) {
  console.error('dist is missing: run npm run build first')
  process.exit(1)
}

const list = (dir, ext) =>
  existsSync(dir) ? readdirSync(dir).filter((f) => !ext || f.endsWith(ext)).map((f) => join(dir, f)) : []

const gzipped = (files) => files.reduce((sum, f) => sum + gzipSync(readFileSync(f)).length, 0)
const raw = (files) => files.reduce((sum, f) => sum + statSync(f).size, 0)

const assets = join(dist, 'assets')
const budgets = [
  { name: 'js', bytes: gzipped(list(assets, '.js')), limit: 200_000 },
  { name: 'css', bytes: gzipped(list(assets, '.css')), limit: 20_000 },
  { name: 'data', bytes: raw(list(join(dist, 'data'))), limit: 8_000_000 },
]

let failed = false
for (const { name, bytes, limit } of budgets) {
  const ok = bytes <= limit
  if (!ok) failed = true
  const fmt = (n) => (n >= 1_000_000 ? `${(n / 1_000_000).toFixed(1)} MB` : `${(n / 1000).toFixed(1)} KB`)
  console.log(`${name} ${fmt(bytes)} / ${fmt(limit)} ${ok ? 'ok' : 'OVER'}`)
}
process.exit(failed ? 1 : 0)
