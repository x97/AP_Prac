export class ApiError extends Error {
  status: number;
  code: string;
  details?: unknown;

  constructor(status: number, code: string, message: string, details?: unknown) {
    super(message);
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

const API_BASE = "/api/v1/admin";

function redirectToLogin() {
  if (typeof window === "undefined") return;
  if (window.location.pathname === "/login") return;
  const next = encodeURIComponent(window.location.pathname + window.location.search);
  window.location.href = `/login?next=${next}`;
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers || {});
  if (init.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers,
    credentials: "include",
    cache: "no-store",
  });
  if (response.status === 401 && !path.startsWith("/auth/login")) {
    redirectToLogin();
    throw new ApiError(401, "ADMIN_AUTH_REQUIRED", "请先登录");
  }
  if (!response.ok) {
    let payload: { code?: string; message?: string; details?: unknown } = {};
    try {
      payload = await response.json();
    } catch {
      // Ignore non-JSON errors.
    }
    throw new ApiError(
      response.status,
      payload.code || "REQUEST_FAILED",
      payload.message || `请求失败（${response.status}）`,
      payload.details,
    );
  }
  return (await response.json()) as T;
}

export const apiGet = <T>(path: string) => api<T>(path);
export const apiPost = <T>(path: string, body?: unknown) =>
  api<T>(path, {
    method: "POST",
    body: body === undefined ? undefined : JSON.stringify(body),
  });

export async function apiUpload<T>(path: string, form: FormData): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    body: form,
    credentials: "include",
    cache: "no-store",
  });
  if (response.status === 401) {
    redirectToLogin();
    throw new ApiError(401, "ADMIN_AUTH_REQUIRED", "请先登录");
  }
  if (!response.ok) {
    let payload: { code?: string; message?: string; details?: unknown } = {};
    try {
      payload = await response.json();
    } catch {
      // Ignore non-JSON errors.
    }
    throw new ApiError(
      response.status,
      payload.code || "REQUEST_FAILED",
      payload.message || `请求失败（${response.status}）`,
      payload.details,
    );
  }
  return (await response.json()) as T;
}

export const apiPatch = <T>(path: string, body?: unknown) =>
  api<T>(path, {
    method: "PATCH",
    body: body === undefined ? undefined : JSON.stringify(body),
  });

export const apiPut = <T>(path: string, body?: unknown) =>
  api<T>(path, {
    method: "PUT",
    body: body === undefined ? undefined : JSON.stringify(body),
  });

export const apiDelete = <T>(path: string) => api<T>(path, { method: "DELETE" });

export async function apiDownload(path: string): Promise<{ blob: Blob; filename: string }> {
  const response = await fetch(`${API_BASE}${path}`, {
    credentials: "include",
    cache: "no-store",
  });
  if (response.status === 401) {
    redirectToLogin();
    throw new ApiError(401, "ADMIN_AUTH_REQUIRED", "请先登录");
  }
  if (!response.ok) {
    let payload: { code?: string; message?: string; details?: unknown } = {};
    try {
      payload = await response.json();
    } catch {
      // Ignore non-JSON errors.
    }
    throw new ApiError(
      response.status,
      payload.code || "REQUEST_FAILED",
      payload.message || `请求失败（${response.status}）`,
      payload.details,
    );
  }
  const disposition = response.headers.get("content-disposition") || "";
  const utf8 = disposition.match(/filename\*=UTF-8''([^;]+)/i);
  const plain = disposition.match(/filename="?([^";]+)"?/);
  let filename = plain?.[1] || "download";
  if (utf8?.[1]) {
    try {
      filename = decodeURIComponent(utf8[1]);
    } catch {
      // Keep the plain filename if the UTF-8 value is malformed.
    }
  }
  return {
    blob: await response.blob(),
    filename,
  };
}
