import { API_BASE_URL, apiClient } from "./client";
import type { Book, CoverSearchResult, CoverUpgradeJob } from "./types";

export async function searchBookCovers(params: {
  title?: string;
  author?: string;
  isbn?: string;
}): Promise<CoverSearchResult[]> {
  const response = await apiClient.get<CoverSearchResult[]>("/books/search-covers", {
    params,
  });
  return response.data;
}

export function getCoverPreviewUrl(url: string): string {
  return `${API_BASE_URL}/books/cover-preview?url=${encodeURIComponent(url)}`;
}

export async function uploadBookCover(bookId: number, file: File): Promise<Book> {
  const formData = new FormData();
  formData.append("file", file);
  const response = await apiClient.post<Book>(`/books/${bookId}/cover`, formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return response.data;
}

export async function startCoverUpgradeSearch(bookId: number): Promise<CoverUpgradeJob> {
  const response = await apiClient.post<CoverUpgradeJob>(`/books/${bookId}/cover-upgrade-search`);
  return response.data;
}

export async function getCoverUpgradeSearch(bookId: number, jobId: string): Promise<CoverUpgradeJob> {
  const response = await apiClient.get<CoverUpgradeJob>(`/books/${bookId}/cover-upgrade-search/${jobId}`);
  return response.data;
}
