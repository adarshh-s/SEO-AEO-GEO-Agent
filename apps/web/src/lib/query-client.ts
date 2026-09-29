import { QueryClient } from "@tanstack/react-query";
import { ApiError } from "./api";

export function makeQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 30_000,
        // Don't retry client errors (4xx); retry server/network errors twice.
        retry: (count, error) => !(error instanceof ApiError && error.status < 500) && count < 2,
        refetchOnWindowFocus: false,
      },
    },
  });
}
