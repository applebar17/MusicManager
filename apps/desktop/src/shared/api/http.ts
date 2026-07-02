import type { ApiErrorRead } from "./types";

const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000";

export class ApiError extends Error {
  readonly code: string;
  readonly status: number;

  constructor({ code, message }: ApiErrorRead, status: number) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.status = status;
  }
}

export function getApiBaseUrl() {
  return import.meta.env.VITE_API_BASE_URL ?? DEFAULT_API_BASE_URL;
}

export async function apiGet<T>(path: string, init?: RequestInit): Promise<T> {
  return apiRequest<T>(path, { ...init, method: "GET" });
}

export async function apiPost<TResponse, TBody = unknown>(
  path: string,
  body?: TBody,
  init?: RequestInit,
): Promise<TResponse> {
  return apiRequest<TResponse>(path, {
    ...init,
    method: "POST",
    body: body === undefined ? undefined : JSON.stringify(body),
  });
}

export async function apiPatch<TResponse, TBody = unknown>(
  path: string,
  body: TBody,
  init?: RequestInit,
): Promise<TResponse> {
  return apiRequest<TResponse>(path, {
    ...init,
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export async function apiDelete<TResponse>(path: string, init?: RequestInit): Promise<TResponse> {
  return apiRequest<TResponse>(path, { ...init, method: "DELETE" });
}

export async function apiRequest<T>(path: string, init: RequestInit): Promise<T> {
  const response = await fetch(`${getApiBaseUrl()}${path}`, {
    ...init,
    headers: {
      Accept: "application/json",
      ...(init.body ? { "Content-Type": "application/json" } : {}),
      ...init.headers,
    },
  });

  if (!response.ok) {
    throw await createApiError(response);
  }

  return response.json() as Promise<T>;
}

async function createApiError(response: Response): Promise<ApiError> {
  const fallback = {
    code: "http_error",
    message: `API request failed with status ${response.status}`,
  };

  try {
    const data = (await response.json()) as Partial<ApiErrorRead>;
    return new ApiError(
      {
        code: data.code ?? fallback.code,
        message: data.message ?? fallback.message,
      },
      response.status,
    );
  } catch {
    return new ApiError(fallback, response.status);
  }
}
