import * as Tooltip from "@radix-ui/react-tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { makeQueryClient } from "@/lib/query-client";
import { useState, type ReactNode } from "react";
import { I18nextProvider } from "react-i18next";
import i18n from "@/lib/i18n";

export function Providers({ children, client }: { children: ReactNode; client?: QueryClient }) {
  const [qc] = useState(() => client ?? makeQueryClient());
  return (
    <I18nextProvider i18n={i18n}>
      <QueryClientProvider client={qc}>
        <Tooltip.Provider>{children}</Tooltip.Provider>
      </QueryClientProvider>
    </I18nextProvider>
  );
}
