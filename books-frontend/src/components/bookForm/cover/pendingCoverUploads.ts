// A locally-picked cover file, staged under an object URL until the book is actually saved.
//
// The object URL doubles as the preview `src` and as the cover field's value, so the
// rest of the cover flow keeps treating the cover as a plain URL string. The actual
// bytes are only uploaded when the user saves the book,
// so browsing and cancelling never touches the server.

const pending = new Map<string, File>();

export function isPendingCover(url: string | null | undefined): boolean {
  return !!url && url.startsWith("blob:");
}

/** Stage a picked file and return the object URL to use as the cover value. */
export function stagePendingCover(file: File): string {
  const url = URL.createObjectURL(file);
  pending.set(url, file);
  return url;
}

/** Read the staged file without discarding it, so failed saves can be retried. */
export function getPendingCover(url: string): File | undefined {
  return pending.get(url);
}

/** Release a staged file after upload, replacement, clearing, or unmounting. */
export function discardPendingCover(url: string | null | undefined): void {
  if (isPendingCover(url) && pending.has(url!)) {
    pending.delete(url!);
    URL.revokeObjectURL(url!);
  }
}
