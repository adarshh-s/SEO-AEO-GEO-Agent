import type { TFunction } from "i18next";
import { ApiError } from "./api";

/** Translate an API error code; fall back to the server's English message. */
export function errorMessage(error: unknown, t: TFunction): string {
  if (error instanceof ApiError) {
    const key = `errors.${error.code}`;
    const translated = t(key, { ns: "common", ...error.detail, defaultValue: "" });
    return translated || error.message || t("errors.generic", { ns: "common" });
  }
  if (error instanceof TypeError) return t("errors.network", { ns: "common" });
  return t("errors.generic", { ns: "common" });
}
