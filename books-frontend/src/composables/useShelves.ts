import { useQuery } from "@tanstack/vue-query";
import { getShelves } from "../api/books";
import { queryKeys } from "../query/keys";

export function useShelves() {
  return useQuery({ queryKey: queryKeys.shelves.list(), queryFn: getShelves });
}
