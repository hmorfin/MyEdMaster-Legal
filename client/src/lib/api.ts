const configuredApiBase = (import.meta.env.VITE_DJANGO_API_URL || import.meta.env.VITE_API_URL || "/api/v1") as string;

// Force browser requests through Vite proxy in dev when an absolute URL is provided.
export const API_BASE_URL = configuredApiBase.startsWith("http") ? "/api/v1" : configuredApiBase;