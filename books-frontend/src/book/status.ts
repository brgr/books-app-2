import { ReadingStatus } from '../api/types'

const STATUS_LABELS: Record<ReadingStatus, string> = {
  [ReadingStatus.WANT_TO_READ]: 'Want to read',
  [ReadingStatus.STARTED]: 'Started',
  [ReadingStatus.FINISHED]: 'Finished',
  [ReadingStatus.ABANDONED]: 'Abandoned',
}

const STATUS_COLORS: Record<ReadingStatus, string> = {
  [ReadingStatus.WANT_TO_READ]: 'var(--color-primary)',
  [ReadingStatus.STARTED]: 'var(--color-warning)',
  [ReadingStatus.FINISHED]: 'var(--color-success)',
  [ReadingStatus.ABANDONED]: 'var(--color-text-secondary)',
}

export function getStatusLabel(status: ReadingStatus | null): string {
  return status ? STATUS_LABELS[status] : 'N/A'
}

export function getStatusColor(status: ReadingStatus | null): string {
  return status ? STATUS_COLORS[status] : 'var(--color-text-secondary)'
}
