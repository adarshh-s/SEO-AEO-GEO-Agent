import * as Tooltip from "@radix-ui/react-tooltip";
import { HelpCircle } from "lucide-react";
import { useTranslation } from "react-i18next";

/** Plain-language explanation for SEO jargon (CLAUDE.md §10: tooltips for any jargon). */
export function Jargon({ term, children }: { term: string; children?: React.ReactNode }) {
  const { t } = useTranslation("glossary");
  return (
    <Tooltip.Root delayDuration={150}>
      <Tooltip.Trigger asChild>
        <button
          type="button"
          className="inline-flex items-center gap-1 underline decoration-dotted underline-offset-4"
          aria-label={t(`${term}.title`)}
        >
          {children ?? t(`${term}.title`)}
          <HelpCircle className="text-muted-foreground size-3.5" aria-hidden />
        </button>
      </Tooltip.Trigger>
      <Tooltip.Portal>
        <Tooltip.Content
          sideOffset={6}
          className="bg-foreground text-background z-50 max-w-xs rounded-md px-3 py-2 text-xs shadow-md"
        >
          {t(`${term}.body`)}
          <Tooltip.Arrow className="fill-foreground" />
        </Tooltip.Content>
      </Tooltip.Portal>
    </Tooltip.Root>
  );
}
