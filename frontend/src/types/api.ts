export interface TenantMembership {
  tenant_id: string;
  tenant_name: string;
  tenant_slug: string;
  role: string;
}

export interface Tenant {
  id: string;
  name: string;
  slug: string;
  description?: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface TenantMember {
  id: string;
  tenant_id: string;
  user_id: string;
  role: string;
  is_active: boolean;
  user_email: string;
  user_display_name: string;
  created_at: string;
  updated_at: string;
}

export interface UserProfile {
  id: string;
  email: string;
  display_name: string;
  is_active: boolean;
  last_login_at?: string | null;
  memberships: TenantMembership[];
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface QrCodeSession {
  session_id: string;
  login_url: string;
  qr_terminal: string;
  qr_image_base64: string;
  status: string;
}

export interface QrCodeStatus {
  session_id: string;
  status: string;
  account_id?: string | null;
  username?: string | null;
  uid?: number | null;
  detail?: string | null;
}

export interface BilibiliAccount {
  id: string;
  tenant_id: string;
  uid: number;
  username: string;
  avatar_url?: string | null;
  status: string;
  risk_status: string;
  last_validated_at?: string | null;
  last_refreshed_at?: string | null;
  last_error?: string | null;
}

export interface MonitorTarget {
  id: string;
  tenant_id: string;
  account_id: string;
  oid: number;
  bvid: string;
  title: string;
  owner_mid?: number | null;
  status: string;
  poll_interval: number;
  last_polled_at?: string | null;
}

export interface ImportedTargetCandidate {
  oid: number;
  bvid: string;
  title: string;
  owner_mid?: number | null;
  already_monitored: boolean;
}

export interface CommentItem {
  id: string;
  tenant_id: string;
  target_id: string;
  account_id: string;
  rpid: number;
  root_rpid?: number | null;
  parent_rpid?: number | null;
  oid: number;
  member_mid?: number | null;
  member_name: string;
  message: string;
  posted_at: string;
  like_count: number;
  is_top_level: boolean;
  is_handled: boolean;
  is_replied: boolean;
  raw_payload: Record<string, unknown>;
}

export interface ReplyAction {
  id: string;
  tenant_id: string;
  account_id: string;
  comment_id: string;
  draft_id?: string | null;
  operator_id?: string | null;
  request_payload: Record<string, unknown>;
  response_payload?: Record<string, unknown> | null;
  status: string;
  error_message?: string | null;
  sent_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ReplyDraft {
  id: string;
  tenant_id: string;
  comment_id: string;
  operator_id?: string | null;
  content: string;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface OverviewStats {
  total_comments: number;
  pending_comments: number;
  replied_comments: number;
  total_targets: number;
  total_accounts: number;
  failed_tasks: number;
  reply_rate: number;
  avg_response_minutes?: number | null;
  platform_overview: Array<{
    platform: string;
    comments: number;
    pending_comments: number;
    replied_comments: number;
    targets: number;
    accounts: number;
  }>;
}

export interface TrendPoint {
  day: string;
  comments: number;
  replies: number;
  bilibili_comments: number;
  douyin_comments: number;
  bilibili_replies: number;
  douyin_replies: number;
}

export interface ReplyPerformancePoint {
  day: string;
  sent: number;
  failed: number;
  avg_response_minutes?: number | null;
  bilibili_sent: number;
  douyin_sent: number;
  bilibili_failed: number;
  douyin_failed: number;
}

export interface AccountHealthItem {
  platform: string;
  account_id: string;
  username: string;
  status: string;
  risk_status?: string | null;
  last_error?: string | null;
  pending_comments: number;
}

export interface TaskRun {
  id: string;
  task_name: string;
  task_kind: string;
  status: string;
  started_at: string;
  finished_at?: string | null;
  duration_ms?: number | null;
  detail: Record<string, unknown>;
  error_message?: string | null;
}

export interface AuditLog {
  id: string;
  tenant_id?: string | null;
  user_id?: string | null;
  action: string;
  entity_type: string;
  entity_id?: string | null;
  payload: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface CommentEventItem {
  id: string;
  event_type: string;
  payload: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface CommentDetail extends CommentItem {
  events: CommentEventItem[];
  reply_drafts: ReplyDraft[];
  reply_actions: ReplyAction[];
}

export interface SystemMetrics {
  queue_backlog: number;
  failed_tasks_last_24h: number;
  login_expired_accounts: number;
  active_targets: number;
  risk_accounts: number;
}

export interface WebhookConfig {
  id: string;
  tenant_id: string;
  name: string;
  provider: string;
  is_enabled: boolean;
  created_at: string;
  updated_at: string;
}

export interface WebhookTestResult {
  ok: boolean;
  detail: string;
}

export interface AIReplyStatus {
  enabled: boolean;
  provider: string;
  model: string;
  base_url: string;
  api_mode: string;
  mode: string;
}

export interface AIReplyGenerateResult {
  content: string;
  mode: string;
  sent: boolean;
}

export interface DouyinApp {
  id: string;
  tenant_id: string;
  name: string;
  client_key: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface DouyinAccount {
  id: string;
  tenant_id: string;
  app_id: string;
  open_id: string;
  nickname: string;
  avatar_url?: string | null;
  status: string;
  access_token_expires_at?: string | null;
  last_validated_at?: string | null;
  last_error?: string | null;
  created_at: string;
  updated_at: string;
}

export interface DouyinPersonalLoginSession {
  session_id: string;
  helper_session_id: string;
  status: string;
  login_url?: string | null;
  qr_image_base64?: string | null;
  expires_at: string;
}

export interface DouyinPersonalLoginStatus {
  session_id: string;
  helper_session_id: string;
  status: string;
  account_id?: string | null;
  nickname?: string | null;
  external_user_id?: string | null;
  detail?: string | null;
}

export interface DouyinPersonalAccount {
  id: string;
  tenant_id: string;
  integration_type: "personal";
  nickname: string;
  avatar_url?: string | null;
  external_user_id: string;
  status: string;
  last_validated_at?: string | null;
  last_error?: string | null;
  created_at: string;
  updated_at: string;
}

export interface DouyinTarget {
  id: string;
  tenant_id: string;
  account_id: string;
  item_id: string;
  title: string;
  status: string;
  poll_interval: number;
  last_polled_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface DouyinPersonalTarget {
  id: string;
  tenant_id: string;
  integration_type: "personal";
  account_id: string;
  aweme_id: string;
  video_url?: string | null;
  title: string;
  status: string;
  poll_interval: number;
  last_polled_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface DouyinCommentItem {
  id: string;
  tenant_id: string;
  target_id: string;
  account_id: string;
  comment_id: string;
  parent_comment_id?: string | null;
  user_open_id?: string | null;
  user_nickname: string;
  user_avatar_url?: string | null;
  content: string;
  posted_at: string;
  digg_count: number;
  reply_count: number;
  is_top_level: boolean;
  is_handled: boolean;
  is_replied: boolean;
  raw_payload: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface DouyinPersonalCommentItem {
  id: string;
  tenant_id: string;
  integration_type: "personal";
  target_id: string;
  account_id: string;
  comment_id: string;
  parent_comment_id?: string | null;
  user_external_id?: string | null;
  user_nickname: string;
  user_avatar_url?: string | null;
  content: string;
  posted_at: string;
  digg_count: number;
  reply_count: number;
  is_top_level: boolean;
  is_handled: boolean;
  is_replied: boolean;
  raw_payload: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface DouyinReplyAction {
  id: string;
  tenant_id: string;
  account_id: string;
  comment_id: string;
  operator_id?: string | null;
  content: string;
  response_payload?: Record<string, unknown> | null;
  status: string;
  error_message?: string | null;
  sent_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface DouyinPersonalReplyAction {
  id: string;
  tenant_id: string;
  integration_type: "personal";
  account_id: string;
  comment_id: string;
  operator_id?: string | null;
  content: string;
  response_payload?: Record<string, unknown> | null;
  status: string;
  error_message?: string | null;
  sent_at?: string | null;
  created_at: string;
  updated_at: string;
}

export type PlatformKind = "bilibili" | "douyin";
export type IntegrationKind = "enterprise" | "personal";

export interface PlatformAccount {
  id: string;
  platform: PlatformKind;
  integration_type?: IntegrationKind | null;
  tenant_id: string;
  display_name: string;
  external_id: string;
  avatar_url?: string | null;
  status: string;
  risk_status?: string | null;
  last_validated_at?: string | null;
  last_refreshed_at?: string | null;
  access_token_expires_at?: string | null;
  last_error?: string | null;
  created_at: string;
  updated_at: string;
}

export interface PlatformTarget {
  id: string;
  platform: PlatformKind;
  integration_type?: IntegrationKind | null;
  tenant_id: string;
  account_id: string;
  title: string;
  external_id: string;
  status: string;
  poll_interval: number;
  last_polled_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface PlatformReplyDraft {
  id: string;
  content: string;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface PlatformReplyAction {
  id: string;
  platform: PlatformKind;
  integration_type?: IntegrationKind | null;
  tenant_id: string;
  account_id: string;
  comment_id: string;
  status: string;
  error_message?: string | null;
  sent_at?: string | null;
  content?: string | null;
  created_at: string;
  updated_at: string;
}

export interface PlatformComment {
  id: string;
  platform: PlatformKind;
  integration_type?: IntegrationKind | null;
  tenant_id: string;
  target_id: string;
  account_id: string;
  external_id: string;
  parent_external_id?: string | null;
  author_name: string;
  author_avatar_url?: string | null;
  content: string;
  posted_at: string;
  like_count: number;
  reply_count: number;
  is_top_level: boolean;
  is_handled: boolean;
  is_replied: boolean;
  raw_payload: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface PlatformCommentEvent {
  id: string;
  event_type: string;
  payload: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface PlatformCommentDetail extends PlatformComment {
  events: PlatformCommentEvent[];
  reply_drafts: PlatformReplyDraft[];
  reply_actions: PlatformReplyAction[];
}
