import commonMessages from "@/lib/i18n/messages/common";

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

// Non-React copy: use the same `ap_lang` preference the LanguageProvider
// persists. `api.ts` can be imported outside React, so it cannot use hooks.
function currentLang(): "zh" | "en" {
  if (typeof window === "undefined") return "en";
  try {
    return window.localStorage.getItem("ap_lang") === "zh" ? "zh" : "en";
  } catch {
    return "en";
  }
}

function uiText(zh: string, vars?: Record<string, string | number>): string {
  const template = currentLang() === "zh" ? zh : (commonMessages[zh] ?? zh);
  if (!vars) return template;
  return template.replace(/\{(\w+)\}/g, (_, key: string) =>
    String(vars[key] ?? `{${key}}`),
  );
}

// Backend error messages are Chinese; map the common codes so the English UI
// never falls back to a Chinese `message` payload.
const EN_ERROR_MESSAGES: Record<string, string> = {
  AUTH_REQUIRED: "Please sign in first",
  EMAIL_OR_PASSWORD_INVALID:
    "Email or password is incorrect. If you don't have an account yet, please sign up first.",
  EMAIL_ALREADY_REGISTERED: "This email is already registered. Sign in or reset your password.",
  EMAIL_CODE_EXPIRED: "The verification code has expired. Request a new one.",
  EMAIL_CODE_INVALID: "The verification code is incorrect",
  EMAIL_CODE_LOCKED: "Too many attempts. Request a new verification code.",
  EMAIL_CODE_RATE_LIMITED: "Too many requests. Please wait and try again.",
  EMAIL_SEND_FAILED: "Failed to send the verification email. Please try again later.",
  INVALID_EMAIL: "Enter a valid email address",
  PASSWORD_TOO_SHORT: "Password is too short",
  PASSWORD_TOO_LONG: "Password is too long",
  PASSWORD_INVALID: "Current password is incorrect",
  PASSWORD_REQUIRED: "Set a password first",
  PASSWORD_NOT_SET: "This account has no password yet",
  OLD_PASSWORD_INVALID: "Current password is incorrect",
  EMAIL_ALREADY_BOUND: "This account already has an email",
  EMAIL_BOUND_TO_OTHER_WECHAT: "This email is linked to another WeChat account",
  EMAIL_ACCOUNT_UNAVAILABLE: "This email account is unavailable",
  WECHAT_NOT_CONFIGURED: "WeChat sign-in is not configured yet",
  ACCOUNT_DISABLED: "This account is disabled",
  CONTENT_LOCKED: "This content is locked. Activate the course to view it.",
  CONTENT_KEY_REQUIRED: "This client cannot decrypt the content",
  CONTENT_KEY_INVALID: "Invalid content decryption key",
  ASSET_SIGNATURE_INVALID: "This asset link is invalid or has expired",
  NICKNAME_REQUIRED: "Nickname can't be empty",
  NICKNAME_INVALID: "Nickname contains unsupported characters",
  ORIGIN_REJECTED: "Request origin is not allowed",
  RATE_LIMITED: "Too many requests. Please slow down.",
  REQUEST_FAILED: "Request failed",
};

// Backend error messages are Chinese. The login endpoint also answers 401 for
// a wrong password, so only an explicit AUTH_REQUIRED should redirect; every
// other 401 keeps its own code and message.
const ZH_ERROR_MESSAGES: Record<string, string> = {
  EMAIL_OR_PASSWORD_INVALID:
    "邮箱或密码不正确。如果还没有注册，请先创建账号。",
};

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
  if (!res.ok) {
    let payload: { code?: string; message?: string; details?: unknown } = {};
    try {
      payload = await res.json();
    } catch {
      // ignore non-JSON errors
    }
    const code = payload.code || "REQUEST_FAILED";
    if (res.status === 401 && (code === "AUTH_REQUIRED" || !payload.code)) {
      redirectToLogin();
      throw new ApiError(401, "AUTH_REQUIRED", uiText("请先登录"));
    }
    const message =
      currentLang() === "zh"
        ? (ZH_ERROR_MESSAGES[code] ||
          payload.message ||
          uiText("请求失败（{status}）", { status: res.status }))
        : (EN_ERROR_MESSAGES[code] || `Request failed (${res.status})`);
    throw new ApiError(res.status, code, message, payload.details);
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
