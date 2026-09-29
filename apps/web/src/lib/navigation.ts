/** Only allow same-app relative paths after login (prevents open redirects). */
export function safeNext(next: string | null): string {
  return next && next.startsWith("/") && !next.startsWith("//") ? next : "/app";
}
