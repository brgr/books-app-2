import { ReadingDatePrecision, type ReadingDateValue } from "../api/types";

const DATE_FORMATTER = new Intl.DateTimeFormat(undefined, {
  year: "numeric",
  month: "short",
  day: "numeric",
});

export function formatShortDate(dateStr: string | null): string {
  if (!dateStr) {
    return "N/A";
  }

  const parsedDate = new Date(dateStr);
  if (Number.isNaN(parsedDate.getTime())) {
    return dateStr;
  }

  return DATE_FORMATTER.format(parsedDate);
}

/**
 * Formats a reading date using the user's locale and the date's precision.
 *
 * The examples below assume the user's locale is set to "en-US".
 *
 * @example
 * formatReadingDate({ value: "2024-01-15", precision: ReadingDatePrecision.YEAR });
 * // "2024"
 *
 * @example
 * formatReadingDate({ value: "2024-01-15", precision: ReadingDatePrecision.MONTH });
 * // "Jan 2024"
 *
 * @example
 * formatReadingDate({ value: "2024-01-15", precision: ReadingDatePrecision.DAY });
 * // "Jan 15, 2024"
 *
 * @example
 * formatReadingDate(null);
 * // "Unknown"
 */
export function formatReadingDate(readingDate: ReadingDateValue | null): string {
  if (!readingDate || readingDate.precision === ReadingDatePrecision.UNKNOWN) {
    return "Unknown";
  }

  if (!readingDate.value) {
    return "Unknown";
  }

  const parsedDate = new Date(readingDate.value);
  if (Number.isNaN(parsedDate.getTime())) {
    return readingDate.value;
  }

  if (readingDate.precision === ReadingDatePrecision.YEAR) {
    return new Intl.DateTimeFormat(undefined, { year: "numeric" }).format(parsedDate);
  }
  if (readingDate.precision === ReadingDatePrecision.MONTH) {
    return new Intl.DateTimeFormat(undefined, { year: "numeric", month: "short" }).format(parsedDate);
  }
  return DATE_FORMATTER.format(parsedDate);
}

/**
 * Represents the browser's local calendar day as an ISO timestamp in the local timezone.
 *
 * The example below assumes the browser is in Rome (UTC+02:00).
 *
 * @example
 * localDayValue(new Date(2026, 8, 1, 15, 30));
 * // "2026-09-01T00:00:00+02:00"
 */
export function localDayValue(date: Date): string {
  const pad = (value: number) => String(value).padStart(2, "0");
  const localMidnight = new Date(date.getFullYear(), date.getMonth(), date.getDate());
  const offsetMinutes = -localMidnight.getTimezoneOffset();
  const offsetSign = offsetMinutes >= 0 ? "+" : "-";
  const offsetHours = pad(Math.floor(Math.abs(offsetMinutes) / 60));
  const offsetRemainder = pad(Math.abs(offsetMinutes) % 60);

  return `${localMidnight.getFullYear()}-${pad(localMidnight.getMonth() + 1)}-${pad(localMidnight.getDate())}T00:00:00${offsetSign}${offsetHours}:${offsetRemainder}`;
}
