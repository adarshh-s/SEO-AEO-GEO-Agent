/** Every host comes from env (decision D10). Localhost defaults for development. */
export const API_URL: string =
  import.meta.env.VITE_API_URL ?? (import.meta.env.PROD ? "/api" : "http://localhost:8000");
export const CONTACT_EMAIL: string = import.meta.env.VITE_CONTACT_EMAIL ?? "adarshs18400@gmail.com";
export const CDN_URL: string =
  import.meta.env.VITE_CDN_URL ?? (import.meta.env.PROD ? "/api/cdn" : "http://localhost:8000/cdn");
