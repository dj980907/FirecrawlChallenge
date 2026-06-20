/** Browser / client components use the public host. */
function publicApiBase(): string {
  return process.env.NEXT_PUBLIC_API_URL ?? "";
}

/**
 * Server Components run inside Docker where ``localhost`` is not routable.
 * Prefer ``API_URL`` (e.g. ``http://api``) on the server; fall back to
 * ``NEXT_PUBLIC_API_URL`` for local dev outside Docker.
 */
function serverApiBase(): string {
  return process.env.API_URL ?? publicApiBase();
}

function resolveApiBase(): string {
  return typeof window === "undefined" ? serverApiBase() : publicApiBase();
}

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export async function apiGet<T>(
  path: string,
  options?: { revalidate?: number },
): Promise<T> {
  const apiBase = resolveApiBase();
  if (!apiBase) {
    throw new ApiError(
      "API URL is not configured (set API_URL or NEXT_PUBLIC_API_URL)",
      0,
    );
  }

  const revalidate = options?.revalidate ?? 60;
  const res = await fetch(`${apiBase}${path}`, {
    headers: { Accept: "application/json" },
    ...(revalidate === 0
      ? { cache: "no-store" as const }
      : { next: { revalidate } }),
  });

  if (!res.ok) {
    throw new ApiError(`API ${res.status}: ${path}`, res.status);
  }

  return res.json() as Promise<T>;
}

export async function apiPost<T, B = unknown>(
  path: string,
  body: B,
): Promise<T> {
  const apiBase = resolveApiBase();
  if (!apiBase) {
    throw new ApiError(
      "API URL is not configured (set API_URL or NEXT_PUBLIC_API_URL)",
      0,
    );
  }

  const res = await fetch(`${apiBase}${path}`, {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    throw new ApiError(`API ${res.status}: ${path}`, res.status);
  }

  return res.json() as Promise<T>;
}
