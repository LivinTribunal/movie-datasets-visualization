import type { Columnar, GenreFamilyRow } from './types'

export interface Family {
  family: string
  colour: string
}

/** Distinct families in family_order. */
export function familyList(gf: Columnar<GenreFamilyRow>): Family[] {
  const { family, family_order, colour } = gf.columns
  const seen = new Map<string, { order: number; colour: string }>()
  family.forEach((f, i) => {
    if (!seen.has(f)) seen.set(f, { order: family_order[i], colour: colour[i] })
  })
  return [...seen]
    .sort((a, b) => a[1].order - b[1].order)
    .map(([f, v]) => ({ family: f, colour: v.colour }))
}
