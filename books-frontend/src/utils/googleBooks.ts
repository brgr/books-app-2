const GOOGLE_HOST = /^(books|www|play)\.google\.(com|[a-z]{2}|com?\.[a-z]{2})$/;

/**
 * Return the volume id from a Google Books link, or null if the text isn't one.
 * Handles books.google.<tld>/books?id=…, google.<tld>/books/edition/<title>/<id>
 * and play.google.com/store/books/details?id=….
 */
export function googleBooksIdFromUrl(text: string): string | null {
  let url: URL;
  try {
    url = new URL(text.trim());
  } catch {
    return null;
  }
  if (!GOOGLE_HOST.test(url.hostname)) {
    return null;
  }

  const edition = url.pathname.match(/^\/books\/edition\/[^/]+\/([^/]+)/);
  if (edition) {
    return edition[1];
  }
  if (url.pathname.startsWith("/books") || url.pathname.startsWith("/store/books/")) {
    return url.searchParams.get("id");
  }
  return null;
}

/** Link to a volume's page on Google Books. */
export function googleBooksVolumeUrl(googleBooksId: string): string {
  return `https://books.google.com/books?${new URLSearchParams({ id: googleBooksId })}`;
}
