export const SHAPES = ['KR', 'HR', '4HR', '6HR', 'DE', 'TR', 'PR', 'TY', 'LI', 'PROFIL', 'casting'] as const

export type ShapeType = typeof SHAPES[number]

// Mapping: Infor shape codes → StockShape enum
import type { StockShape } from '@/types/material'

export const SHAPE_TO_STOCK_SHAPE: Record<string, StockShape> = {
  'KR': 'round_bar',      // Kulatá tyč
  'HR': 'flat_bar',       // Hranatý materiál (obdélník)
  '4HR': 'square_bar',    // Čtyřhran
  '6HR': 'hexagonal_bar', // Šestihran
  'DE': 'plate',          // Deska
  'TR': 'tube',           // Trubka
  'PR': 'flat_bar',       // Profil → flat_bar
  'TY': 'round_bar',      // Tyč → round_bar
  'LI': 'casting',        // Litina → casting
  'PROFIL': 'flat_bar',   // Profil
  'casting': 'casting',   // Odlitek
}

export const SHAPE_DIMENSIONS: Record<string, { key: string; label: string }[]> = {
  KR:      [{ key: 'diameter', label: 'Průměr (mm)' }, { key: 'length', label: 'Délka (mm)' }],
  HR:      [{ key: 'width', label: 'Šířka (mm)' }, { key: 'height', label: 'Výška (mm)' }, { key: 'length', label: 'Délka (mm)' }],
  '4HR':   [{ key: 'width', label: 'Šířka (mm)' }, { key: 'length', label: 'Délka (mm)' }],
  '6HR':   [{ key: 'width', label: 'Šířka (mm)' }, { key: 'length', label: 'Délka (mm)' }],
  DE:      [{ key: 'width', label: 'Šířka (mm)' }, { key: 'height', label: 'Výška (mm)' }, { key: 'thickness', label: 'Tloušťka (mm)' }],
  TR:      [{ key: 'diameter', label: 'Průměr (mm)' }, { key: 'thickness', label: 'Tloušťka (mm)' }, { key: 'length', label: 'Délka (mm)' }],
  PR:      [{ key: 'width', label: 'Šířka (mm)' }, { key: 'height', label: 'Výška (mm)' }, { key: 'length', label: 'Délka (mm)' }],
  TY:      [{ key: 'diameter', label: 'Průměr (mm)' }, { key: 'length', label: 'Délka (mm)' }],
  LI:      [{ key: 'width', label: 'Šířka (mm)' }, { key: 'height', label: 'Výška (mm)' }, { key: 'thickness', label: 'Tloušťka (mm)' }],
  PROFIL:  [{ key: 'width', label: 'Šířka (mm)' }, { key: 'height', label: 'Výška (mm)' }, { key: 'length', label: 'Délka (mm)' }],
  casting: [{ key: 'width', label: 'Šířka (mm)' }, { key: 'height', label: 'Výška (mm)' }, { key: 'length', label: 'Délka (mm)' }],
}

export function formatDimensions(mat: { diameter?: number; width?: number; height?: number; thickness?: number; length?: number }): string {
  const parts: string[] = []
  if (mat.diameter) parts.push(`D${mat.diameter}`)
  if (mat.width) parts.push(`${mat.width}`)
  if (mat.height) parts.push(`x${mat.height}`)
  if (mat.thickness) parts.push(`t${mat.thickness}`)
  if (mat.length) parts.push(`L${mat.length}`)
  return parts.join(' ') || '—'
}

export function matchTypeBadgeClass(matchType: string): string {
  switch (matchType) {
    case 'exact': return 'bg-green-500/20 text-green-400'
    case 'norm': return 'bg-blue-500/20 text-blue-400'
    case 'partial': return 'bg-yellow-500/20 text-yellow-400'
    case 'manual': return 'bg-purple-500/20 text-purple-400'
    default: return 'bg-gray-500/20 text-gray-400'
  }
}
