export function partStatusLabel(status: string | null | undefined): string {
  switch (status) {
    case 'active': return 'Aktivní'
    case 'inactive': return 'Neaktivní'
    case 'archived': return 'Archivován'
    case 'draft': return 'Koncept'
    default: return status ?? '—'
  }
}

export function partSourceLabel(source: string | null | undefined): string {
  switch (source) {
    case 'manual': return 'Manuální'
    case 'infor': return 'Infor'
    case 'import': return 'Import'
    case 'copy': return 'Kopie'
    default: return source ?? '—'
  }
}

export function quoteStatusLabel(status: string | null | undefined): string {
  switch (status) {
    case 'draft': return 'Koncept'
    case 'sent': return 'Odesláno'
    case 'approved': return 'Schváleno'
    case 'rejected': return 'Zamítnuto'
    case 'expired': return 'Vypršelo'
    default: return status ?? '—'
  }
}
