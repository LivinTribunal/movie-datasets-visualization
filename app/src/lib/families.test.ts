import { expect, it } from 'vitest'
import { familyList } from './families'
import type { Columnar, GenreFamilyRow } from './types'

it('returns distinct families in family_order', () => {
  const gf = {
    columns: {
      genre: ['A', 'B', 'C'],
      family: ['Two', 'One', 'Two'],
      family_order: [2, 1, 2],
      colour: ['#222', '#111', '#222'],
    },
  } as Columnar<GenreFamilyRow>
  expect(familyList(gf)).toEqual([
    { family: 'One', colour: '#111' },
    { family: 'Two', colour: '#222' },
  ])
})
