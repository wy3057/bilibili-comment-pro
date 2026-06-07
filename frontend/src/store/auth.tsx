import React, { createContext, useContext, useEffect, useState } from "react";
import { App } from "antd";
import { fetchMe, login as loginRequest, logoutSession } from "../api/endpoints";
import { clearStoredTokens, persistTokens } from "../api/client";
import type { TenantMembership, UserProfile } from "../types/api";

type AuthContextValue = {
  token: string | null;
  refreshToken: string | null;
  user: UserProfile | null;
  activeTenant: TenantMembership | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  setActiveTenantById: (tenantId: string, membershipsOverride?: TenantMembership[]) => void;
  reloadProfile: () => Promise<UserProfile | null>;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

const TENANT_KEY = "bili_comment_active_tenant_id";

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const { message } = App.useApp();
  const [token, setToken] = useState<string | null>(localStorage.getItem("bili_comment_access_token"));
  const [refreshToken, setRefreshToken] = useState<string | null>(localStorage.getItem("bili_comment_refresh_token"));
  const [user, setUser] = useState<UserProfile | null>(null);
  const [activeTenant, setActiveTenant] = useState<TenantMembership | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  function applyActiveTenant(tenantId: string, memberships?: TenantMembership[]) {
    const source = memberships || user?.memberships || [];
    const tenant = source.find((item) => item.tenant_id === tenantId) || null;
    setActiveTenant(tenant);
    if (tenant) {
      localStorage.setItem(TENANT_KEY, tenant.tenant_id);
    }
  }

  async function reloadProfile(): Promise<UserProfile | null> {
    if (!token) {
      setUser(null);
      setActiveTenant(null);
      return null;
    }

    const profile = await fetchMe(token);
    setUser(profile);
    const savedTenant = localStorage.getItem(TENANT_KEY);
    const selected =
      profile.memberships.find((item) => item.tenant_id === savedTenant) || profile.memberships[0] || null;
    setActiveTenant(selected);
    if (selected) {
      localStorage.setItem(TENANT_KEY, selected.tenant_id);
    }
    return profile;
  }

  useEffect(() => {
    async function hydrate() {
      if (!token) {
        setLoading(false);
        return;
      }
      try {
        await reloadProfile();
      } catch (error) {
        console.error(error);
        clearStoredTokens();
        setToken(null);
        setRefreshToken(null);
      } finally {
        setLoading(false);
      }
    }
    hydrate();
  }, [token]);

  useEffect(() => {
    function syncTokens(event: Event) {
      const detail = (event as CustomEvent<{ accessToken: string; refreshToken: string } | null>).detail;
      setToken(detail?.accessToken || null);
      setRefreshToken(detail?.refreshToken || null);
    }

    window.addEventListener("bili-comment-auth-changed", syncTokens as EventListener);
    return () => {
      window.removeEventListener("bili-comment-auth-changed", syncTokens as EventListener);
    };
  }, []);

  async function login(email: string, password: string) {
    const tokens = await loginRequest(email, password);
    persistTokens({
      accessToken: tokens.access_token,
      refreshToken: tokens.refresh_token,
    });
    setToken(tokens.access_token);
    setRefreshToken(tokens.refresh_token);
    const profile = await fetchMe(tokens.access_token);
    setUser(profile);
    const tenant = profile.memberships[0] || null;
    setActiveTenant(tenant);
    if (tenant) {
      localStorage.setItem(TENANT_KEY, tenant.tenant_id);
    }
    message.success("登录成功");
  }

  function logout() {
    if (token && refreshToken) {
      logoutSession(token, refreshToken).catch(() => undefined);
    }
    clearStoredTokens();
    localStorage.removeItem(TENANT_KEY);
    setToken(null);
    setRefreshToken(null);
    setUser(null);
    setActiveTenant(null);
  }

  function setActiveTenantById(tenantId: string, membershipsOverride?: TenantMembership[]) {
    applyActiveTenant(tenantId, membershipsOverride);
  }

  return (
    <AuthContext.Provider
      value={{
        token,
        refreshToken,
        user,
        activeTenant,
        loading,
        login,
        logout,
        setActiveTenantById,
        reloadProfile,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) {
    throw new Error("AuthProvider missing");
  }
  return value;
}
