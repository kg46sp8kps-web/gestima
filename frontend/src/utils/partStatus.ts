/**
 * partStatus.ts — Single source of truth pro status/source labely a dot třídy dílu
 *
 * DŮVOD EXISTENCE: Zabraňuje duplicitám a nekonzistentním překladům napříč komponentami.
 * Všechny komponenty MUSÍ importovat odsud — nikdy nedefinovat lokálně!
 */

// ─── STATUS ────────────────────────────────────────────────────────────────

export function partStatusLabel(status: string): string {
  switch (status) {
    case 'active':   return 'Aktivní'
    case 'draft':    return 'Rozpracovaný'
    case 'archived': return 'Archivovaný'
    case 'quote':    return 'Nabídka'
    default:         return status
  }
}

export function partStatusDotClass(status: string): string {
  switch (status) {
    case 'active':   return 'badge-dot-ok'
    case 'draft':    return 'badge-dot-warn'
    case 'quote':    return 'badge-dot-brand'
    case 'archived': return 'badge-dot-neutral'
    default:         return 'badge-dot-neutral'
  }
}

// ─── SOURCE ────────────────────────────────────────────────────────────────

export function partSourceLabel(source: string): string {
  switch (source) {
    case 'infor_import':  return 'Infor Import'
    case 'manual':        return 'Manuální'
    case 'quote_request': return 'Poptávka'
    default:              return source
  }
}

export function partSourceDotClass(source: string): string {
  switch (source) {
    case 'infor_import':  return 'badge-dot-brand'
    case 'manual':        return 'badge-dot-ok'
    case 'quote_request': return 'badge-dot-warn'
    default:              return 'badge-dot-neutral'
  }
}
