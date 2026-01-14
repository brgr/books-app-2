const DATE_FORMATTER = new Intl.DateTimeFormat(undefined, {
  year: 'numeric',
  month: 'short',
  day: 'numeric',
})

export function formatShortDate(dateStr: string | null): string {
  if (!dateStr) return 'N/A'

  const parsedDate = new Date(dateStr)
  if (Number.isNaN(parsedDate.getTime())) {
    return dateStr
  }

  return DATE_FORMATTER.format(parsedDate)
}
