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

const API_BASE = "/api/v1";
const SECURE_PREFIXES = [
  "/attempts",
  "/practice-sessions",
  "/practice-groups",
  "/papers",
  "/knowledge-graph",
  "/me",
  "/flashcards",
  "/question-reports",
];

function isSecurePath(path: string) {
  return SECURE_PREFIXES.some(
    (prefix) => path === prefix || path.startsWith(`${prefix}/`) || path.startsWith(`${prefix}?`),
  );
}

function bytesToBase64(value: ArrayBuffer): string {
  const bytes = new Uint8Array(value);
  let binary = "";
  const chunk = 0x8000;
  for (let i = 0; i < bytes.length; i += chunk) {
    binary += String.fromCharCode(...bytes.subarray(i, i + chunk));
  }
  return btoa(binary);
}

function base64ToBytes(value: string): ArrayBuffer {
  const binary = atob(value);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i += 1) bytes[i] = binary.charCodeAt(i);
  return bytes.buffer;
}

type EncryptedEnvelope = {
  encrypted: true;
  v: number;
  alg: string;
  server_public_key: string;
  salt: string;
  iv: string;
  ciphertext: string;
};

async function decryptEnvelope(
  envelope: EncryptedEnvelope,
  privateKey: CryptoKey,
  aad: string,
): Promise<unknown> {
  const serverPublicKey = await crypto.subtle.importKey(
    "raw",
    base64ToBytes(envelope.server_public_key),
    { name: "ECDH", namedCurve: "P-256" },
    false,
    [],
  );
  const shared = await crypto.subtle.deriveBits(
    { name: "ECDH", public: serverPublicKey },
    privateKey,
    256,
  );
  const hkdfKey = await crypto.subtle.importKey("raw", shared, "HKDF", false, ["deriveKey"]);
  const aesKey = await crypto.subtle.deriveKey(
    {
      name: "HKDF",
      hash: "SHA-256",
      salt: base64ToBytes(envelope.salt),
      info: new TextEncoder().encode("ap-content-v1"),
    },
    hkdfKey,
    { name: "AES-GCM", length: 256 },
    false,
    ["decrypt"],
  );
  const plaintext = await crypto.subtle.decrypt(
    {
      name: "AES-GCM",
      iv: base64ToBytes(envelope.iv),
      additionalData: new TextEncoder().encode(aad),
      tagLength: 128,
    },
    aesKey,
    base64ToBytes(envelope.ciphertext),
  );
  return JSON.parse(new TextDecoder().decode(plaintext));
}

let clientKeyCache:
  | { privateKey: CryptoKey; publicB64: string; expiresAt: number }
  | null = null;

async function clientKey() {
  if (clientKeyCache && clientKeyCache.expiresAt > Date.now()) return clientKeyCache;
  const keyPair = (await crypto.subtle.generateKey(
    { name: "ECDH", namedCurve: "P-256" },
    true,
    ["deriveBits"],
  )) as CryptoKeyPair;
  const publicRaw = await crypto.subtle.exportKey("raw", keyPair.publicKey);
  clientKeyCache = {
    privateKey: keyPair.privateKey,
    publicB64: bytesToBase64(publicRaw),
    expiresAt: Date.now() + 10 * 60 * 1000,
  };
  return clientKeyCache;
}

async function secureRequestKey(method: string, path: string) {
  if (
    typeof window === "undefined" ||
    !window.crypto?.subtle ||
    !isSecurePath(path)
  ) {
    return null;
  }
  const key = await clientKey();
  const url = new URL(`${API_BASE}${path}`, window.location.origin);
  return {
    header: key.publicB64,
    privateKey: key.privateKey,
    aad: `ap-content-v1|${method.toUpperCase()}|${url.pathname}`,
  };
}

function redirectToLogin() {
  if (typeof window === "undefined") return;
  if (window.location.pathname === "/login") return;
  const next = encodeURIComponent(window.location.pathname + window.location.search);
  window.location.replace(`/login?next=${next}`);
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const method = (init.method || "GET").toUpperCase();
  const headers = new Headers(init.headers || {});
  if (init.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const secure = await secureRequestKey(method, path);
  if (secure) headers.set("X-Content-Pubkey", secure.header);
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers,
    credentials: "include",
    cache: "no-store",
  });
  if (res.status === 401) {
    redirectToLogin();
    throw new ApiError(401, "AUTH_REQUIRED", "请先登录");
  }
  if (!res.ok) {
    let payload: { code?: string; message?: string; details?: unknown } = {};
    try {
      payload = await res.json();
    } catch {
      // ignore non-JSON errors
    }
    throw new ApiError(
      res.status,
      payload.code || "REQUEST_FAILED",
      payload.message || `请求失败（${res.status}）`,
      payload.details,
    );
  }
  if (res.status === 204) return undefined as T;
  if (res.headers.get("x-content-encrypted") === "1" && secure) {
    const envelope = (await res.json()) as EncryptedEnvelope;
    return (await decryptEnvelope(envelope, secure.privateKey, secure.aad)) as T;
  }
  return (await res.json()) as T;
}

export const apiGet = <T>(path: string) => api<T>(path);
export const apiPost = <T>(path: string, body?: unknown) =>
  api<T>(path, { method: "POST", body: body === undefined ? undefined : JSON.stringify(body) });
export const apiPatch = <T>(path: string, body?: unknown) =>
  api<T>(path, { method: "PATCH", body: body === undefined ? undefined : JSON.stringify(body) });
export const apiPut = <T>(path: string, body?: unknown) =>
  api<T>(path, { method: "PUT", body: body === undefined ? undefined : JSON.stringify(body) });
export const apiDelete = <T>(path: string) => api<T>(path, { method: "DELETE" });
