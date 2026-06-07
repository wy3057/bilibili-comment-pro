const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api";
const ACCESS_KEY = "bili_comment_access_token";
const REFRESH_KEY = "bili_comment_refresh_token";

type RequestOptions = {
  method?: string;
  body?: unknown;
  token?: string | null;
  tenantId?: string | null;
  retryOnAuth?: boolean;
};

type TokenPair = {
  accessToken: string;
  refreshToken: string;
};

function notifyTokenChange(tokens: TokenPair | null) {
  window.dispatchEvent(
    new CustomEvent("bili-comment-auth-changed", {
      detail: tokens,
    })
  );
}

function getStoredAccessToken(): string | null {
  return localStorage.getItem(ACCESS_KEY);
}

function getStoredRefreshToken(): string | null {
  return localStorage.getItem(REFRESH_KEY);
}

export function persistTokens(tokens: TokenPair) {
  localStorage.setItem(ACCESS_KEY, tokens.accessToken);
  localStorage.setItem(REFRESH_KEY, tokens.refreshToken);
  notifyTokenChange(tokens);
}

export function clearStoredTokens() {
  localStorage.removeItem(ACCESS_KEY);
  localStorage.removeItem(REFRESH_KEY);
  notifyTokenChange(null);
}

let refreshPromise: Promise<TokenPair | null> | null = null;

async function refreshAccessToken(): Promise<TokenPair | null> {
  const refreshToken = getStoredRefreshToken();
  if (!refreshToken) return null;
  if (!refreshPromise) {
    refreshPromise = fetch(`${API_BASE_URL}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    })
      .then(async (response) => {
        if (!response.ok) {
          return null;
        }
        const body = (await response.json()) as {
          access_token: string;
          refresh_token: string;
        };
        const tokens = {
          accessToken: body.access_token,
          refreshToken: body.refresh_token,
        };
        persistTokens(tokens);
        return tokens;
      })
      .finally(() => {
        refreshPromise = null;
      });
  }
  return refreshPromise;
}

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };

  const accessToken = getStoredAccessToken() || options.token;
  if (accessToken) {
    headers.Authorization = `Bearer ${accessToken}`;
  }
  if (options.tenantId) {
    headers["X-Tenant-Id"] = options.tenantId;
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: options.method || "GET",
    headers,
    body: options.body ? JSON.stringify(options.body) : undefined,
  });

  if (response.status === 401 && options.retryOnAuth !== false) {
    const refreshed = await refreshAccessToken();
    if (refreshed) {
      return apiRequest<T>(path, {
        ...options,
        token: refreshed.accessToken,
        retryOnAuth: false,
      });
    }
    clearStoredTokens();
  }

  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Request failed: ${response.status}`);
  }

  return response.json() as Promise<T>;
}
