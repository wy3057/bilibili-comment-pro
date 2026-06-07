import { apiRequest } from "./client";
import type {
  AIReplyGenerateResult,
  AIReplyStatus,
  AccountHealthItem,
  AuditLog,
  BilibiliAccount,
  CommentDetail,
  CommentItem,
  DouyinAccount,
  DouyinApp,
  DouyinCommentItem,
  DouyinPersonalAccount,
  DouyinPersonalCommentItem,
  DouyinPersonalLoginSession,
  DouyinPersonalLoginStatus,
  DouyinPersonalReplyAction,
  DouyinPersonalTarget,
  DouyinReplyAction,
  DouyinTarget,
  ImportedTargetCandidate,
  MonitorTarget,
  OverviewStats,
  PlatformAccount,
  PlatformComment,
  PlatformCommentDetail,
  PlatformReplyAction,
  PlatformTarget,
  QrCodeSession,
  QrCodeStatus,
  ReplyAction,
  ReplyPerformancePoint,
  SystemMetrics,
  TaskRun,
  Tenant,
  TenantMember,
  TokenResponse,
  TrendPoint,
  UserProfile,
  WebhookConfig,
  WebhookTestResult,
} from "../types/api";

export function login(email: string, password: string) {
  return apiRequest<TokenResponse>("/auth/login", {
    method: "POST",
    body: { email, password },
    retryOnAuth: false,
  });
}

export function refreshSession(refreshToken: string) {
  return apiRequest<TokenResponse>("/auth/refresh", {
    method: "POST",
    body: { refresh_token: refreshToken },
    retryOnAuth: false,
  });
}

export function logoutSession(token: string, refreshToken: string) {
  return apiRequest<{ message: string }>("/auth/logout", {
    method: "POST",
    token,
    body: { refresh_token: refreshToken },
    retryOnAuth: false,
  });
}

export function fetchMe(token: string) {
  return apiRequest<UserProfile>("/auth/me", { token });
}

export function fetchTenants(token: string) {
  return apiRequest<Tenant[]>("/tenants", { token });
}

export function createTenant(
  token: string,
  payload: {
    name: string;
    slug: string;
    description?: string;
  }
) {
  return apiRequest<Tenant>("/tenants", {
    method: "POST",
    token,
    body: payload,
  });
}

export function fetchTenantMembers(token: string, tenantId: string) {
  return apiRequest<TenantMember[]>(`/tenants/${tenantId}/members`, { token, tenantId });
}

export function createTenantMember(
  token: string,
  tenantId: string,
  payload: {
    email: string;
    display_name?: string;
    password?: string;
    role: string;
  }
) {
  return apiRequest<TenantMember>(`/tenants/${tenantId}/members`, {
    method: "POST",
    token,
    tenantId,
    body: payload,
  });
}

export function updateTenantMember(
  token: string,
  tenantId: string,
  memberId: string,
  payload: {
    role?: string;
    is_active?: boolean;
  }
) {
  return apiRequest<TenantMember>(`/tenants/${tenantId}/members/${memberId}`, {
    method: "PATCH",
    token,
    tenantId,
    body: payload,
  });
}

export function fetchOverview(token: string, tenantId: string) {
  return apiRequest<OverviewStats>("/analytics/overview", { token, tenantId });
}

export function fetchAccounts(token: string, tenantId: string) {
  return apiRequest<BilibiliAccount[]>("/bilibili/accounts", { token, tenantId });
}

export function startQrLogin(token: string, tenantId: string) {
  return apiRequest<QrCodeSession>("/bilibili/accounts/qrcode/start", {
    method: "POST",
    token,
    tenantId,
  });
}

export function checkQrLogin(token: string, tenantId: string, sessionId: string) {
  return apiRequest<QrCodeStatus>(`/bilibili/accounts/qrcode/${sessionId}`, {
    token,
    tenantId,
  });
}

export function importCredentials(
  token: string,
  tenantId: string,
  payload: {
    sessdata: string;
    bili_jct: string;
    buvid3?: string;
    buvid4?: string;
    dedeuserid?: string;
    ac_time_value?: string;
  }
) {
  return apiRequest<BilibiliAccount>("/bilibili/accounts/import-credentials", {
    method: "POST",
    token,
    tenantId,
    body: payload,
  });
}

export function refreshAccount(token: string, tenantId: string, accountId: string) {
  return apiRequest<BilibiliAccount>(`/bilibili/accounts/${accountId}/refresh`, {
    method: "POST",
    token,
    tenantId,
  });
}

export function fetchTargets(token: string, tenantId: string) {
  return apiRequest<MonitorTarget[]>("/targets", { token, tenantId });
}

export function createTarget(
  token: string,
  tenantId: string,
  payload: {
    account_id: string;
    oid: number;
    bvid: string;
    title: string;
    owner_mid?: number;
    poll_interval?: number;
  }
) {
  return apiRequest<MonitorTarget>("/targets", {
    method: "POST",
    token,
    tenantId,
    body: payload,
  });
}

export function importTargets(token: string, tenantId: string, accountId: string, onlyMissing = true) {
  return apiRequest<MonitorTarget[]>(`/targets/import-from-account/${accountId}`, {
    method: "POST",
    token,
    tenantId,
    body: { only_missing: onlyMissing },
  });
}

export function fetchTargetImportPreview(token: string, tenantId: string, accountId: string) {
  return apiRequest<ImportedTargetCandidate[]>(`/targets/import-preview/${accountId}`, {
    token,
    tenantId,
  });
}

export function importSelectedTargets(
  token: string,
  tenantId: string,
  accountId: string,
  payload: { only_missing: boolean; selected_bvids?: string[]; poll_interval: number }
) {
  return apiRequest<MonitorTarget[]>(`/targets/import-from-account/${accountId}`, {
    method: "POST",
    token,
    tenantId,
    body: payload,
  });
}

export function fetchComments(token: string, tenantId: string) {
  return apiRequest<CommentItem[]>("/comments", { token, tenantId });
}

export function fetchCommentDetail(token: string, tenantId: string, commentId: string) {
  return apiRequest<CommentDetail>(`/comments/${commentId}`, { token, tenantId });
}

export function markCommentsHandled(
  token: string,
  tenantId: string,
  payload: { comment_ids: string[]; is_handled: boolean }
) {
  return apiRequest<{ updated: number }>("/comments/handled", {
    method: "PATCH",
    token,
    tenantId,
    body: payload,
  });
}

export function createReplyDraft(
  token: string,
  tenantId: string,
  payload: { comment_id: string; content: string }
) {
  return apiRequest<{ id: string; status: string }>("/reply-drafts", {
    method: "POST",
    token,
    tenantId,
    body: payload,
  });
}

export function sendReply(
  token: string,
  tenantId: string,
  payload: {
    comment_id: string;
    account_id: string;
    content?: string;
    draft_id?: string;
  }
) {
  return apiRequest<ReplyAction>("/reply-actions/send", {
    method: "POST",
    token,
    tenantId,
    body: payload,
  });
}

export function pollTarget(token: string, tenantId: string, targetId: string) {
  return apiRequest<{ created: number; sub_replies: number }>(`/comments/target/${targetId}/poll`, {
    method: "POST",
    token,
    tenantId,
  });
}

export function fetchReplyActions(token: string, tenantId: string) {
  return apiRequest<ReplyAction[]>("/reply-actions", { token, tenantId });
}

export function fetchOpsAccounts(
  token: string,
  tenantId: string,
  platform?: string,
  integrationType?: string
) {
  const query = new URLSearchParams();
  if (platform && platform !== "all") query.set("platform", platform);
  if (integrationType && integrationType !== "all") query.set("integration_type", integrationType);
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return apiRequest<PlatformAccount[]>(`/ops/accounts${suffix}`, { token, tenantId });
}

export function fetchOpsTargets(
  token: string,
  tenantId: string,
  platform?: string,
  integrationType?: string
) {
  const query = new URLSearchParams();
  if (platform && platform !== "all") query.set("platform", platform);
  if (integrationType && integrationType !== "all") query.set("integration_type", integrationType);
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return apiRequest<PlatformTarget[]>(`/ops/targets${suffix}`, { token, tenantId });
}

export function fetchOpsComments(
  token: string,
  tenantId: string,
  params?: {
    platform?: string;
    integration_type?: string;
    target_id?: string;
    account_id?: string;
    is_handled?: boolean;
    is_replied?: boolean;
    keyword?: string;
  }
) {
  const query = new URLSearchParams();
  if (params?.platform && params.platform !== "all") query.set("platform", params.platform);
  if (params?.integration_type && params.integration_type !== "all") {
    query.set("integration_type", params.integration_type);
  }
  if (params?.target_id) query.set("target_id", params.target_id);
  if (params?.account_id) query.set("account_id", params.account_id);
  if (params?.is_handled !== undefined) query.set("is_handled", String(params.is_handled));
  if (params?.is_replied !== undefined) query.set("is_replied", String(params.is_replied));
  if (params?.keyword) query.set("keyword", params.keyword);
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return apiRequest<PlatformComment[]>(`/ops/comments${suffix}`, { token, tenantId });
}

export function fetchOpsCommentDetail(
  token: string,
  tenantId: string,
  platform: string,
  commentId: string,
  integrationType?: string
) {
  const suffix =
    integrationType && integrationType !== "all"
      ? `?integration_type=${encodeURIComponent(integrationType)}`
      : "";
  return apiRequest<PlatformCommentDetail>(`/ops/comments/${platform}/${commentId}${suffix}`, { token, tenantId });
}

export function markOpsCommentsHandled(
  token: string,
  tenantId: string,
  payload: { items: Array<{ platform: string; id: string }>; is_handled: boolean }
) {
  return apiRequest<{ updated: number }>("/ops/comments/handled", {
    method: "PATCH",
    token,
    tenantId,
    body: payload,
  });
}

export function fetchOpsReplyActions(
  token: string,
  tenantId: string,
  params?: { platform?: string; integration_type?: string; status?: string; account_id?: string }
) {
  const query = new URLSearchParams();
  if (params?.platform && params.platform !== "all") query.set("platform", params.platform);
  if (params?.integration_type && params.integration_type !== "all") {
    query.set("integration_type", params.integration_type);
  }
  if (params?.status) query.set("status", params.status);
  if (params?.account_id) query.set("account_id", params.account_id);
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return apiRequest<PlatformReplyAction[]>(`/ops/reply-actions${suffix}`, { token, tenantId });
}

export function sendOpsReply(
  token: string,
  tenantId: string,
  payload: {
    platform: string;
    integration_type?: string;
    comment_id: string;
    account_id: string;
    content?: string;
    draft_id?: string;
  }
) {
  return apiRequest<PlatformReplyAction>("/ops/replies/send", {
    method: "POST",
    token,
    tenantId,
    body: payload,
  });
}

export function generateOpsReply(
  token: string,
  tenantId: string,
  payload: {
    platform: string;
    integration_type?: string;
    comment_id: string;
    account_id: string;
    extra_instruction?: string;
  }
) {
  return apiRequest<AIReplyGenerateResult>("/ops/replies/generate", {
    method: "POST",
    token,
    tenantId,
    body: payload,
  });
}

export function fetchDouyinApps(token: string, tenantId: string) {
  return apiRequest<DouyinApp[]>("/douyin/apps", { token, tenantId });
}

export function createDouyinApp(
  token: string,
  tenantId: string,
  payload: { name: string; client_key: string; client_secret: string }
) {
  return apiRequest<DouyinApp>("/douyin/apps", {
    method: "POST",
    token,
    tenantId,
    body: payload,
  });
}

export function startDouyinOAuth(
  token: string,
  tenantId: string,
  payload: { app_id: string; redirect_path?: string }
) {
  return apiRequest<{ session_id: string; state: string; auth_url: string; expires_at: string }>("/douyin/oauth/start", {
    method: "POST",
    token,
    tenantId,
    body: payload,
  });
}

export function exchangeDouyinOAuthCode(
  token: string,
  tenantId: string,
  payload: { app_id: string; code: string }
) {
  return apiRequest<DouyinAccount>("/douyin/oauth/exchange-code", {
    method: "POST",
    token,
    tenantId,
    body: payload,
  });
}

export function fetchDouyinAccounts(token: string, tenantId: string) {
  return apiRequest<DouyinAccount[]>("/douyin/accounts", { token, tenantId });
}

export function refreshDouyinAccount(token: string, tenantId: string, accountId: string) {
  return apiRequest<DouyinAccount>(`/douyin/accounts/${accountId}/refresh`, {
    method: "POST",
    token,
    tenantId,
  });
}

export function importDouyinAuthorization(
  token: string,
  tenantId: string,
  payload: {
    app_id: string;
    open_id: string;
    access_token: string;
    refresh_token?: string;
    nickname?: string;
    avatar_url?: string;
    access_token_expires_at?: string;
  }
) {
  return apiRequest<DouyinAccount>("/douyin/accounts/import-authorization", {
    method: "POST",
    token,
    tenantId,
    body: payload,
  });
}

export function fetchDouyinTargets(token: string, tenantId: string) {
  return apiRequest<DouyinTarget[]>("/douyin/targets", { token, tenantId });
}

export function createDouyinTarget(
  token: string,
  tenantId: string,
  payload: { account_id: string; item_id: string; title: string; poll_interval?: number }
) {
  return apiRequest<DouyinTarget>("/douyin/targets", {
    method: "POST",
    token,
    tenantId,
    body: payload,
  });
}

export function pollDouyinTarget(token: string, tenantId: string, targetId: string) {
  return apiRequest<{ created: number }>(`/douyin/targets/${targetId}/poll`, {
    method: "POST",
    token,
    tenantId,
  });
}

export function fetchDouyinComments(
  token: string,
  tenantId: string,
  params?: { target_id?: string; is_handled?: boolean }
) {
  const query = new URLSearchParams();
  if (params?.target_id) query.set("target_id", params.target_id);
  if (params?.is_handled !== undefined) query.set("is_handled", String(params.is_handled));
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return apiRequest<DouyinCommentItem[]>(`/douyin/comments${suffix}`, { token, tenantId });
}

export function markDouyinCommentsHandled(
  token: string,
  tenantId: string,
  payload: { comment_ids: string[]; is_handled: boolean }
) {
  return apiRequest<{ updated: number }>("/douyin/comments/handled", {
    method: "PATCH",
    token,
    tenantId,
    body: payload,
  });
}

export function fetchDouyinReplyActions(token: string, tenantId: string) {
  return apiRequest<DouyinReplyAction[]>("/douyin/reply-actions", { token, tenantId });
}

export function sendDouyinReply(
  token: string,
  tenantId: string,
  payload: { comment_id: string; account_id: string; content: string }
) {
  return apiRequest<DouyinReplyAction>("/douyin/reply-actions/send", {
    method: "POST",
    token,
    tenantId,
    body: payload,
  });
}

export function startDouyinPersonalLogin(token: string, tenantId: string) {
  return apiRequest<DouyinPersonalLoginSession>("/douyin/personal/login/start", {
    method: "POST",
    token,
    tenantId,
  });
}

export function fetchDouyinPersonalLoginStatus(token: string, tenantId: string, sessionId: string) {
  return apiRequest<DouyinPersonalLoginStatus>(`/douyin/personal/login/${sessionId}`, {
    token,
    tenantId,
  });
}

export function fetchDouyinPersonalAccounts(token: string, tenantId: string) {
  return apiRequest<DouyinPersonalAccount[]>("/douyin/personal/accounts", { token, tenantId });
}

export function importDouyinPersonalCookie(
  token: string,
  tenantId: string,
  payload: {
    cookie: string;
    nickname?: string;
    avatar_url?: string;
    external_user_id?: string;
  }
) {
  return apiRequest<DouyinPersonalAccount>("/douyin/personal/accounts/import-cookie", {
    method: "POST",
    token,
    tenantId,
    body: payload,
  });
}

export function refreshDouyinPersonalAccount(token: string, tenantId: string, accountId: string) {
  return apiRequest<DouyinPersonalAccount>(`/douyin/personal/accounts/${accountId}/refresh-runtime`, {
    method: "POST",
    token,
    tenantId,
  });
}

export function fetchDouyinPersonalTargets(token: string, tenantId: string) {
  return apiRequest<DouyinPersonalTarget[]>("/douyin/personal/targets", { token, tenantId });
}

export function createDouyinPersonalTarget(
  token: string,
  tenantId: string,
  payload: { account_id: string; aweme_id?: string; video_url?: string; title?: string; poll_interval?: number }
) {
  return apiRequest<DouyinPersonalTarget>("/douyin/personal/targets", {
    method: "POST",
    token,
    tenantId,
    body: payload,
  });
}

export function pollDouyinPersonalTarget(token: string, tenantId: string, targetId: string) {
  return apiRequest<{ created: number }>(`/douyin/personal/targets/${targetId}/poll`, {
    method: "POST",
    token,
    tenantId,
  });
}

export function fetchDouyinPersonalComments(
  token: string,
  tenantId: string,
  params?: { target_id?: string; is_handled?: boolean }
) {
  const query = new URLSearchParams();
  if (params?.target_id) query.set("target_id", params.target_id);
  if (params?.is_handled !== undefined) query.set("is_handled", String(params.is_handled));
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return apiRequest<DouyinPersonalCommentItem[]>(`/douyin/personal/comments${suffix}`, { token, tenantId });
}

export function markDouyinPersonalCommentsHandled(
  token: string,
  tenantId: string,
  payload: { comment_ids: string[]; is_handled: boolean }
) {
  return apiRequest<{ updated: number }>("/douyin/personal/comments/handled", {
    method: "PATCH",
    token,
    tenantId,
    body: payload,
  });
}

export function fetchDouyinPersonalReplyActions(token: string, tenantId: string) {
  return apiRequest<DouyinPersonalReplyAction[]>("/douyin/personal/reply-actions", { token, tenantId });
}

export function sendDouyinPersonalReply(
  token: string,
  tenantId: string,
  payload: { comment_id: string; account_id: string; content: string }
) {
  return apiRequest<DouyinPersonalReplyAction>("/douyin/personal/reply-actions/send", {
    method: "POST",
    token,
    tenantId,
    body: payload,
  });
}

export function fetchCommentTrends(token: string, tenantId: string) {
  return apiRequest<TrendPoint[]>("/analytics/comments/trends", { token, tenantId });
}

export function fetchReplyPerformance(token: string, tenantId: string) {
  return apiRequest<ReplyPerformancePoint[]>("/analytics/replies/performance", { token, tenantId });
}

export function fetchAccountHealth(token: string, tenantId: string) {
  return apiRequest<AccountHealthItem[]>("/analytics/accounts/health", { token, tenantId });
}

export function fetchTaskRuns(token: string, tenantId: string) {
  return apiRequest<TaskRun[]>("/system/jobs", { token, tenantId });
}

export function fetchSystemMetrics(token: string, tenantId: string) {
  return apiRequest<SystemMetrics>("/system/metrics", { token, tenantId });
}

export function fetchAIReplyStatus(token: string, tenantId: string) {
  return apiRequest<AIReplyStatus>("/system/ai-reply", { token, tenantId });
}

export function updateAIReplyMode(token: string, tenantId: string, mode: string) {
  return apiRequest<AIReplyStatus>("/system/ai-reply/mode", {
    method: "PATCH",
    token,
    tenantId,
    body: { mode },
  });
}

export function fetchAuditLogs(token: string, tenantId: string) {
  return apiRequest<AuditLog[]>("/audit-logs", { token, tenantId });
}

export function fetchWebhooks(token: string, tenantId: string) {
  return apiRequest<WebhookConfig[]>("/notifications/webhooks", { token, tenantId });
}

export function createWebhook(
  token: string,
  tenantId: string,
  payload: { name: string; provider: string; webhook_url: string; is_enabled?: boolean }
) {
  return apiRequest<WebhookConfig>("/notifications/webhooks", {
    method: "POST",
    token,
    tenantId,
    body: payload,
  });
}

export function updateWebhook(
  token: string,
  tenantId: string,
  webhookId: string,
  payload: { name?: string; provider?: string; webhook_url?: string; is_enabled?: boolean }
) {
  return apiRequest<WebhookConfig>(`/notifications/webhooks/${webhookId}`, {
    method: "PATCH",
    token,
    tenantId,
    body: payload,
  });
}

export function deleteWebhook(token: string, tenantId: string, webhookId: string) {
  return apiRequest<{ message: string }>(`/notifications/webhooks/${webhookId}`, {
    method: "DELETE",
    token,
    tenantId,
  });
}

export function testWebhook(token: string, tenantId: string, webhookId: string) {
  return apiRequest<WebhookTestResult>(`/notifications/webhooks/${webhookId}/test`, {
    method: "POST",
    token,
    tenantId,
  });
}
