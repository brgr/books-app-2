import { uploadBookCover } from "../../../api/covers";
import { discardPendingCover, getPendingCover } from "./pendingCoverUploads";

export async function savePendingCover(bookId: number, cover: string, file = getPendingCover(cover)): Promise<string> {
  if (!file) {
    return cover;
  }

  const book = await uploadBookCover(bookId, file);
  // Preserve the staged file if the upload fails, so saving can be retried.
  discardPendingCover(cover);
  return book.cover_image_url ?? "";
}
