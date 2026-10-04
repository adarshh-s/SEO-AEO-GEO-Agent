/** Display names of AI answer engines (brand names, not translated). */
const ENGINE_NAMES: Record<string, string> = {
  chatgpt: "ChatGPT",
  gemini: "Gemini",
  perplexity: "Perplexity",
  claude: "Claude",
  copilot: "Copilot",
};

export function engineName(id: string): string {
  return ENGINE_NAMES[id] ?? id;
}
