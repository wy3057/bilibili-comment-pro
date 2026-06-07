import {
  Alert,
  App,
  Button,
  Card,
  Drawer,
  Form,
  Image,
  Input,
  InputNumber,
  Modal,
  Select,
  Space,
  Spin,
  Table,
  Tabs,
  Tag,
  Typography,
} from "antd";
import { Key, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import {
  checkQrLogin,
  createDouyinApp,
  createDouyinPersonalTarget,
  createReplyDraft,
  createTarget,
  createDouyinTarget,
  exchangeDouyinOAuthCode,
  fetchAccounts,
  fetchAIReplyStatus,
  fetchDouyinAccounts,
  fetchDouyinApps,
  fetchDouyinPersonalAccounts,
  fetchDouyinPersonalLoginStatus,
  fetchOpsAccounts,
  fetchOpsCommentDetail,
  fetchOpsComments,
  fetchOpsReplyActions,
  fetchOpsTargets,
  fetchTargetImportPreview,
  generateOpsReply,
  importCredentials,
  importDouyinAuthorization,
  importDouyinPersonalCookie,
  importSelectedTargets,
  markOpsCommentsHandled,
  pollDouyinPersonalTarget,
  pollDouyinTarget,
  pollTarget,
  refreshAccount,
  refreshDouyinAccount,
  refreshDouyinPersonalAccount,
  sendOpsReply,
  startDouyinOAuth,
  startDouyinPersonalLogin,
  startQrLogin,
} from "../api/endpoints";
import { PageHeader } from "../components/PageHeader";
import { useAuth } from "../store/auth";
import type {
  AIReplyStatus,
  BilibiliAccount,
  DouyinAccount,
  DouyinApp,
  DouyinPersonalAccount,
  DouyinPersonalLoginSession,
  DouyinPersonalLoginStatus,
  ImportedTargetCandidate,
  IntegrationKind,
  PlatformAccount,
  PlatformComment,
  PlatformCommentDetail,
  PlatformReplyAction,
  PlatformTarget,
  QrCodeSession,
  QrCodeStatus,
} from "../types/api";
import { formatDateTime } from "../utils/format";
import { useTenantRealtime } from "../utils/realtime";

const { Paragraph, Text } = Typography;

type TabKey = "accounts" | "targets" | "inbox" | "replies";
type PlatformFilter = "all" | "bilibili" | "douyin";
type IntegrationFilter = "all" | "enterprise" | "personal";

type BilibiliCredentialImportValues = {
  sessdata: string;
  bili_jct: string;
  buvid3?: string;
  buvid4?: string;
  dedeuserid?: string;
  ac_time_value?: string;
};

type DouyinAppFormValues = {
  name: string;
  client_key: string;
  client_secret: string;
};

type DouyinTokenImportValues = {
  app_id: string;
  open_id: string;
  access_token: string;
  refresh_token?: string;
  nickname?: string;
  avatar_url?: string;
};

type DouyinCodeImportValues = {
  app_id: string;
  code: string;
};

type DouyinPersonalCookieImportValues = {
  cookie: string;
  nickname?: string;
  avatar_url?: string;
  external_user_id?: string;
};

type BilibiliTargetCreateValues = {
  account_id: string;
  oid: number;
  bvid: string;
  title: string;
  owner_mid?: number;
  poll_interval?: number;
};

type DouyinTargetCreateValues = {
  account_id: string;
  item_id: string;
  title: string;
  poll_interval?: number;
};

type DouyinPersonalTargetCreateValues = {
  account_id: string;
  aweme_id?: string;
  video_url?: string;
  title?: string;
  poll_interval?: number;
};

type ReplyFormValues = {
  account_id: string;
  content: string;
};

function isTabKey(value: string | null): value is TabKey {
  return value === "accounts" || value === "targets" || value === "inbox" || value === "replies";
}

function isPlatformFilter(value: string | null): value is PlatformFilter {
  return value === "all" || value === "bilibili" || value === "douyin";
}

function makeRowKey(platform: string, integrationType: string | null | undefined, id: string) {
  return `${platform}:${integrationType || "default"}:${id}`;
}

function parseRowKey(key: Key) {
  const [platform, integration_type, id] = String(key).split(":");
  return {
    platform,
    integration_type: integration_type === "default" ? undefined : integration_type,
    id,
  };
}

export function OpsPage() {
  const { message } = App.useApp();
  const { token, activeTenant } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();

  const tabParam = searchParams.get("tab");
  const platformParam = searchParams.get("platform");
  const currentTab: TabKey = isTabKey(tabParam) ? tabParam : "inbox";
  const currentPlatform: PlatformFilter = isPlatformFilter(platformParam)
    ? platformParam
    : "all";
  const [integrationFilter, setIntegrationFilter] = useState<IntegrationFilter>("all");

  const [opsAccounts, setOpsAccounts] = useState<PlatformAccount[]>([]);
  const [opsTargets, setOpsTargets] = useState<PlatformTarget[]>([]);
  const [opsComments, setOpsComments] = useState<PlatformComment[]>([]);
  const [opsReplyActions, setOpsReplyActions] = useState<PlatformReplyAction[]>([]);
  const [aiReplyStatus, setAiReplyStatus] = useState<AIReplyStatus | null>(null);

  const [bilibiliAccounts, setBilibiliAccounts] = useState<BilibiliAccount[]>([]);
  const [douyinApps, setDouyinApps] = useState<DouyinApp[]>([]);
  const [douyinAccounts, setDouyinAccounts] = useState<DouyinAccount[]>([]);
  const [douyinPersonalAccounts, setDouyinPersonalAccounts] = useState<DouyinPersonalAccount[]>([]);

  const [selectedComment, setSelectedComment] = useState<PlatformComment | null>(null);
  const [selectedDetail, setSelectedDetail] = useState<PlatformCommentDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  const [keyword, setKeyword] = useState("");
  const [handledFilter, setHandledFilter] = useState<"all" | "handled" | "pending">("all");
  const [repliedFilter, setRepliedFilter] = useState<"all" | "replied" | "unreplied">("all");
  const [typeFilter, setTypeFilter] = useState<"all" | "top" | "sub">("all");
  const [accountFilter, setAccountFilter] = useState<string>("all");
  const [targetFilter, setTargetFilter] = useState<string>("all");

  const [selectedCommentKeys, setSelectedCommentKeys] = useState<Key[]>([]);
  const [loading, setLoading] = useState(false);
  const [aiLoading, setAiLoading] = useState(false);
  const [aiInstruction, setAiInstruction] = useState("");

  const [biliCredentialOpen, setBiliCredentialOpen] = useState(false);
  const [biliQrOpen, setBiliQrOpen] = useState(false);
  const [douyinAppOpen, setDouyinAppOpen] = useState(false);
  const [douyinTokenOpen, setDouyinTokenOpen] = useState(false);
  const [douyinCodeOpen, setDouyinCodeOpen] = useState(false);
  const [douyinOauthOpen, setDouyinOauthOpen] = useState(false);
  const [douyinPersonalLoginOpen, setDouyinPersonalLoginOpen] = useState(false);
  const [douyinPersonalCookieOpen, setDouyinPersonalCookieOpen] = useState(false);
  const [biliTargetCreateOpen, setBiliTargetCreateOpen] = useState(false);
  const [biliTargetImportOpen, setBiliTargetImportOpen] = useState(false);
  const [douyinTargetOpen, setDouyinTargetOpen] = useState(false);
  const [douyinPersonalTargetOpen, setDouyinPersonalTargetOpen] = useState(false);

  const [biliTargetCandidates, setBiliTargetCandidates] = useState<ImportedTargetCandidate[]>([]);
  const [selectedCandidateKeys, setSelectedCandidateKeys] = useState<React.Key[]>([]);

  const [qrSession, setQrSession] = useState<QrCodeSession | null>(null);
  const [qrStatus, setQrStatus] = useState<QrCodeStatus | null>(null);
  const [douyinPersonalLoginSession, setDouyinPersonalLoginSession] = useState<DouyinPersonalLoginSession | null>(null);
  const [douyinPersonalLoginStatus, setDouyinPersonalLoginStatus] = useState<DouyinPersonalLoginStatus | null>(null);

  const [biliCredentialForm] = Form.useForm<BilibiliCredentialImportValues>();
  const [douyinAppForm] = Form.useForm<DouyinAppFormValues>();
  const [douyinTokenForm] = Form.useForm<DouyinTokenImportValues>();
  const [douyinCodeForm] = Form.useForm<DouyinCodeImportValues>();
  const [douyinPersonalCookieForm] = Form.useForm<DouyinPersonalCookieImportValues>();
  const [biliTargetCreateForm] = Form.useForm<BilibiliTargetCreateValues>();
  const [biliTargetImportForm] = Form.useForm<{ account_id: string; poll_interval?: number }>();
  const [douyinTargetForm] = Form.useForm<DouyinTargetCreateValues>();
  const [douyinPersonalTargetForm] = Form.useForm<DouyinPersonalTargetCreateValues>();
  const [replyForm] = Form.useForm<ReplyFormValues>();
  const [douyinOauthForm] = Form.useForm<{ app_id: string }>();

  const realtimeVersion = useTenantRealtime(token, activeTenant?.tenant_id);

  function updateQuery(next: Partial<Record<"tab" | "platform", string>>) {
    const params = new URLSearchParams(searchParams);
    Object.entries(next).forEach(([key, value]) => {
      if (value) params.set(key, value);
      else params.delete(key);
    });
    setSearchParams(params);
  }

  useEffect(() => {
    if (currentPlatform !== "douyin" && integrationFilter !== "all") {
      setIntegrationFilter("all");
    }
  }, [currentPlatform, integrationFilter]);

  async function loadMeta() {
    if (!token || !activeTenant) return;
    const [accounts, targets, rawBiliAccounts, apps, rawDouyinAccounts, rawDouyinPersonalAccounts, aiStatus] =
      await Promise.all([
      fetchOpsAccounts(token, activeTenant.tenant_id, currentPlatform, integrationFilter),
      fetchOpsTargets(token, activeTenant.tenant_id, currentPlatform, integrationFilter),
      fetchAccounts(token, activeTenant.tenant_id),
      fetchDouyinApps(token, activeTenant.tenant_id),
      fetchDouyinAccounts(token, activeTenant.tenant_id),
      fetchDouyinPersonalAccounts(token, activeTenant.tenant_id),
      fetchAIReplyStatus(token, activeTenant.tenant_id),
    ]);
    setOpsAccounts(accounts);
    setOpsTargets(targets);
    setBilibiliAccounts(rawBiliAccounts);
    setDouyinApps(apps);
    setDouyinAccounts(rawDouyinAccounts);
    setDouyinPersonalAccounts(rawDouyinPersonalAccounts);
    setAiReplyStatus(aiStatus);
  }

  async function loadTabData() {
    if (!token || !activeTenant) return;
    if (currentTab === "inbox") {
      const comments = await fetchOpsComments(token, activeTenant.tenant_id, {
        platform: currentPlatform,
        integration_type: integrationFilter,
        account_id: accountFilter === "all" ? undefined : accountFilter,
        target_id: targetFilter === "all" ? undefined : targetFilter,
        is_handled: handledFilter === "all" ? undefined : handledFilter === "handled",
        is_replied: repliedFilter === "all" ? undefined : repliedFilter === "replied",
        keyword: keyword || undefined,
      });
      const filtered = comments.filter((item) => {
        if (typeFilter === "top" && !item.is_top_level) return false;
        if (typeFilter === "sub" && item.is_top_level) return false;
        return true;
      });
      setOpsComments(filtered);
      return;
    }
    if (currentTab === "replies") {
      setOpsReplyActions(
        await fetchOpsReplyActions(token, activeTenant.tenant_id, {
          platform: currentPlatform,
          integration_type: integrationFilter,
        })
      );
    }
  }

  useEffect(() => {
    loadMeta().catch(console.error);
    loadTabData().catch(console.error);
  }, [
    token,
    activeTenant,
    realtimeVersion,
    currentTab,
    currentPlatform,
    integrationFilter,
    keyword,
    handledFilter,
    repliedFilter,
    typeFilter,
    accountFilter,
    targetFilter,
  ]);

  useEffect(() => {
    const oauth = searchParams.get("oauth");
    if (!oauth) return;
    if (oauth === "success") message.success("抖音 OAuth 授权成功");
    else if (oauth === "failed") message.error("抖音 OAuth 授权失败");
    else message.warning(`抖音 OAuth 状态：${oauth}`);
    const params = new URLSearchParams(searchParams);
    params.delete("oauth");
    setSearchParams(params);
  }, [searchParams.toString()]);

  useEffect(() => {
    if (!biliQrOpen || !qrSession || !token || !activeTenant) return;
    const timer = window.setInterval(async () => {
      try {
        const status = await checkQrLogin(token, activeTenant.tenant_id, qrSession.session_id);
        setQrStatus(status);
        if (status.status === "done") {
          await loadMeta();
          message.success(`已绑定 B站账号 ${status.username || status.uid}`);
          window.clearInterval(timer);
        }
      } catch (error) {
        console.error(error);
      }
    }, 3000);
    return () => window.clearInterval(timer);
  }, [biliQrOpen, qrSession, token, activeTenant]);

  useEffect(() => {
    if (!douyinPersonalLoginOpen || !douyinPersonalLoginSession || !token || !activeTenant) return;
    const timer = window.setInterval(async () => {
      try {
        const status = await fetchDouyinPersonalLoginStatus(
          token,
          activeTenant.tenant_id,
          douyinPersonalLoginSession.session_id
        );
        setDouyinPersonalLoginStatus(status);
        if (status.status === "done") {
          await loadMeta();
          message.success(`已绑定抖音个人账号 ${status.nickname || status.external_user_id}`);
          window.clearInterval(timer);
        }
      } catch (error) {
        console.error(error);
      }
    }, 3000);
    return () => window.clearInterval(timer);
  }, [douyinPersonalLoginOpen, douyinPersonalLoginSession, token, activeTenant]);

  const biliQrImageSrc = useMemo(() => {
    if (!qrSession) return "";
    return `data:image/png;base64,${qrSession.qr_image_base64}`;
  }, [qrSession]);

  const douyinPersonalQrImageSrc = useMemo(() => {
    if (!douyinPersonalLoginSession?.qr_image_base64) return "";
    return `data:image/png;base64,${douyinPersonalLoginSession.qr_image_base64}`;
  }, [douyinPersonalLoginSession]);

  const platformScopedAccountOptions = useMemo(() => {
    if (!selectedComment) return [];
    if (selectedComment.platform === "bilibili") {
      return bilibiliAccounts.map((item) => ({
        label: `${item.username} (${item.uid})`,
        value: item.id,
      }));
    }
    if (selectedComment.integration_type === "personal") {
      return douyinPersonalAccounts.map((item) => ({
        label: `${item.nickname} (${item.external_user_id})`,
        value: item.id,
      }));
    }
    return douyinAccounts.map((item) => ({
      label: `${item.nickname} (${item.open_id})`,
      value: item.id,
    }));
  }, [selectedComment, bilibiliAccounts, douyinAccounts, douyinPersonalAccounts]);

  const accountOptions = useMemo(
    () => [{ label: "全部账号", value: "all" }, ...opsAccounts.map((item) => ({
      label: `${item.platform === "bilibili" ? "B站" : `抖音${item.integration_type === "personal" ? "·个人" : "·企业"}`} · ${item.display_name}`,
      value: item.id,
    }))],
    [opsAccounts]
  );

  const targetOptions = useMemo(
    () => [{ label: "全部目标", value: "all" }, ...opsTargets.map((item) => ({
      label: `${item.platform === "bilibili" ? "B站" : `抖音${item.integration_type === "personal" ? "·个人" : "·企业"}`} · ${item.title}`,
      value: item.id,
    }))],
    [opsTargets]
  );

  async function openCommentDetail(comment: PlatformComment) {
    if (!token || !activeTenant) return;
    setSelectedComment(comment);
    setSelectedDetail(null);
    setDetailLoading(true);
    try {
      const detail = await fetchOpsCommentDetail(
        token,
        activeTenant.tenant_id,
        comment.platform,
        comment.id,
        comment.integration_type || undefined
      );
      setSelectedDetail(detail);
      replyForm.setFieldsValue({ account_id: detail.account_id });
    } catch (error) {
      message.error(error instanceof Error ? error.message : "加载评论详情失败");
    } finally {
      setDetailLoading(false);
    }
  }

  async function onStartBiliQrLogin() {
    if (!token || !activeTenant) return;
    setLoading(true);
    try {
      const session = await startQrLogin(token, activeTenant.tenant_id);
      setQrSession(session);
      setQrStatus(null);
      setBiliQrOpen(true);
    } catch (error) {
      message.error(error instanceof Error ? error.message : "无法启动 B站二维码登录");
    } finally {
      setLoading(false);
    }
  }

  async function onImportBiliCredentials(values: BilibiliCredentialImportValues) {
    if (!token || !activeTenant) return;
    setLoading(true);
    try {
      await importCredentials(token, activeTenant.tenant_id, values);
      setBiliCredentialOpen(false);
      biliCredentialForm.resetFields();
      await loadMeta();
      message.success("B站凭证导入成功");
    } catch (error) {
      message.error(error instanceof Error ? error.message : "B站凭证导入失败");
    } finally {
      setLoading(false);
    }
  }

  async function onCreateDouyinApp(values: DouyinAppFormValues) {
    if (!token || !activeTenant) return;
    setLoading(true);
    try {
      await createDouyinApp(token, activeTenant.tenant_id, values);
      setDouyinAppOpen(false);
      douyinAppForm.resetFields();
      await loadMeta();
      message.success("抖音应用已创建");
    } catch (error) {
      message.error(error instanceof Error ? error.message : "抖音应用创建失败");
    } finally {
      setLoading(false);
    }
  }

  async function onStartDouyinOauth(values: { app_id: string }) {
    if (!token || !activeTenant) return;
    try {
      const session = await startDouyinOAuth(token, activeTenant.tenant_id, {
        app_id: values.app_id,
        redirect_path: "/ops?tab=accounts&platform=douyin",
      });
      window.open(session.auth_url, "_blank", "noopener,noreferrer");
      setDouyinOauthOpen(false);
      message.success("已打开抖音授权页");
    } catch (error) {
      message.error(error instanceof Error ? error.message : "启动抖音 OAuth 失败");
    }
  }

  async function onImportDouyinToken(values: DouyinTokenImportValues) {
    if (!token || !activeTenant) return;
    setLoading(true);
    try {
      await importDouyinAuthorization(token, activeTenant.tenant_id, values);
      setDouyinTokenOpen(false);
      douyinTokenForm.resetFields();
      await loadMeta();
      message.success("抖音授权账号已导入");
    } catch (error) {
      message.error(error instanceof Error ? error.message : "抖音授权导入失败");
    } finally {
      setLoading(false);
    }
  }

  async function onExchangeDouyinCode(values: DouyinCodeImportValues) {
    if (!token || !activeTenant) return;
    setLoading(true);
    try {
      await exchangeDouyinOAuthCode(token, activeTenant.tenant_id, values);
      setDouyinCodeOpen(false);
      douyinCodeForm.resetFields();
      await loadMeta();
      message.success("抖音授权码交换成功");
    } catch (error) {
      message.error(error instanceof Error ? error.message : "抖音授权码交换失败");
    } finally {
      setLoading(false);
    }
  }

  async function onStartDouyinPersonalLogin() {
    if (!token || !activeTenant) return;
    setLoading(true);
    try {
      const session = await startDouyinPersonalLogin(token, activeTenant.tenant_id);
      setDouyinPersonalLoginSession(session);
      setDouyinPersonalLoginStatus(null);
      setDouyinPersonalLoginOpen(true);
    } catch (error) {
      message.error(error instanceof Error ? error.message : "启动抖音个人登录失败");
    } finally {
      setLoading(false);
    }
  }

  async function onImportDouyinPersonalCookie(values: DouyinPersonalCookieImportValues) {
    if (!token || !activeTenant) return;
    setLoading(true);
    try {
      await importDouyinPersonalCookie(token, activeTenant.tenant_id, values);
      setDouyinPersonalCookieOpen(false);
      douyinPersonalCookieForm.resetFields();
      await loadMeta();
      message.success("抖音个人 Cookie 已导入");
    } catch (error) {
      message.error(error instanceof Error ? error.message : "抖音个人 Cookie 导入失败");
    } finally {
      setLoading(false);
    }
  }

  async function onRefreshPlatformAccount(account: PlatformAccount) {
    if (!token || !activeTenant) return;
    try {
      if (account.platform === "bilibili") {
        await refreshAccount(token, activeTenant.tenant_id, account.id);
      } else if (account.integration_type === "personal") {
        await refreshDouyinPersonalAccount(token, activeTenant.tenant_id, account.id);
      } else {
        await refreshDouyinAccount(token, activeTenant.tenant_id, account.id);
      }
      await loadMeta();
      message.success("账号刷新完成");
    } catch (error) {
      message.error(error instanceof Error ? error.message : "账号刷新失败");
    }
  }

  async function onCreateBiliTarget(values: BilibiliTargetCreateValues) {
    if (!token || !activeTenant) return;
    setLoading(true);
    try {
      await createTarget(token, activeTenant.tenant_id, {
        ...values,
        poll_interval: values.poll_interval || 300,
      });
      setBiliTargetCreateOpen(false);
      biliTargetCreateForm.resetFields();
      await loadMeta();
      message.success("B站监控目标已添加");
    } catch (error) {
      message.error(error instanceof Error ? error.message : "B站目标添加失败");
    } finally {
      setLoading(false);
    }
  }

  async function onLoadBiliImportPreview(accountId: string) {
    if (!token || !activeTenant) return;
    const rows = await fetchTargetImportPreview(token, activeTenant.tenant_id, accountId);
    setBiliTargetCandidates(rows);
    setSelectedCandidateKeys(rows.filter((item) => !item.already_monitored).map((item) => item.bvid));
  }

  async function onImportBiliTargets(values: { account_id: string; poll_interval?: number }) {
    if (!token || !activeTenant) return;
    setLoading(true);
    try {
      await importSelectedTargets(token, activeTenant.tenant_id, values.account_id, {
        only_missing: true,
        selected_bvids: selectedCandidateKeys.map(String),
        poll_interval: values.poll_interval || 300,
      });
      setBiliTargetImportOpen(false);
      biliTargetImportForm.resetFields();
      setBiliTargetCandidates([]);
      setSelectedCandidateKeys([]);
      await loadMeta();
      message.success("B站稿件已导入");
    } catch (error) {
      message.error(error instanceof Error ? error.message : "B站稿件导入失败");
    } finally {
      setLoading(false);
    }
  }

  async function onCreateDouyinTarget(values: DouyinTargetCreateValues) {
    if (!token || !activeTenant) return;
    setLoading(true);
    try {
      await createDouyinTarget(token, activeTenant.tenant_id, {
        ...values,
        poll_interval: values.poll_interval || 300,
      });
      setDouyinTargetOpen(false);
      douyinTargetForm.resetFields();
      await loadMeta();
      message.success("抖音监控目标已添加");
    } catch (error) {
      message.error(error instanceof Error ? error.message : "抖音目标添加失败");
    } finally {
      setLoading(false);
    }
  }

  async function onCreateDouyinPersonalTarget(values: DouyinPersonalTargetCreateValues) {
    if (!token || !activeTenant) return;
    setLoading(true);
    try {
      await createDouyinPersonalTarget(token, activeTenant.tenant_id, {
        ...values,
        poll_interval: values.poll_interval || 300,
      });
      setDouyinPersonalTargetOpen(false);
      douyinPersonalTargetForm.resetFields();
      await loadMeta();
      message.success("抖音个人监控目标已添加");
    } catch (error) {
      message.error(error instanceof Error ? error.message : "抖音个人目标添加失败");
    } finally {
      setLoading(false);
    }
  }

  async function onPollPlatformTarget(target: PlatformTarget) {
    if (!token || !activeTenant) return;
    try {
      if (target.platform === "bilibili") {
        await pollTarget(token, activeTenant.tenant_id, target.id);
      } else if (target.integration_type === "personal") {
        await pollDouyinPersonalTarget(token, activeTenant.tenant_id, target.id);
      } else {
        await pollDouyinTarget(token, activeTenant.tenant_id, target.id);
      }
      await loadMeta();
      await loadTabData();
      message.success("目标同步完成");
    } catch (error) {
      message.error(error instanceof Error ? error.message : "目标同步失败");
    }
  }

  async function onMarkHandled(
    items: Array<{ platform: string; id: string; integration_type?: string }>,
    isHandled: boolean
  ) {
    if (!token || !activeTenant || items.length === 0) return;
    try {
      await markOpsCommentsHandled(token, activeTenant.tenant_id, { items, is_handled: isHandled });
      await loadTabData();
      message.success("评论处理状态已更新");
    } catch (error) {
      message.error(error instanceof Error ? error.message : "更新评论状态失败");
    }
  }

  async function onCreateDraft() {
    if (!token || !activeTenant || !selectedComment || selectedComment.platform !== "bilibili") return;
    const content = replyForm.getFieldValue("content");
    if (!content) return;
    try {
      await createReplyDraft(token, activeTenant.tenant_id, {
        comment_id: selectedComment.id,
        content,
      });
      const detail = await fetchOpsCommentDetail(
        token,
        activeTenant.tenant_id,
        selectedComment.platform,
        selectedComment.id,
        selectedComment.integration_type || undefined
      );
      setSelectedDetail(detail);
      message.success("草稿已创建");
    } catch (error) {
      message.error(error instanceof Error ? error.message : "创建草稿失败");
    }
  }

  async function onGenerateAIReply() {
    if (!token || !activeTenant || !selectedComment) return;
    const accountId = replyForm.getFieldValue("account_id");
    if (!accountId) {
      message.warning("请先选择回复账号");
      return;
    }
    setAiLoading(true);
    try {
      const result = await generateOpsReply(token, activeTenant.tenant_id, {
        platform: selectedComment.platform,
        integration_type: selectedComment.integration_type || undefined,
        comment_id: selectedComment.id,
        account_id: accountId,
        extra_instruction: aiInstruction || undefined,
      });
      replyForm.setFieldValue("content", result.content);
      if (result.sent) {
        setSelectedComment(null);
        setSelectedDetail(null);
        replyForm.resetFields();
        await loadTabData();
        message.success("AI 已生成并直接发送");
      } else {
        message.success("AI 已生成建议稿");
      }
    } catch (error) {
      message.error(error instanceof Error ? error.message : "AI 生成失败");
    } finally {
      setAiLoading(false);
    }
  }

  async function onSendReply(values: ReplyFormValues) {
    if (!token || !activeTenant || !selectedComment) return;
    setLoading(true);
    try {
      await sendOpsReply(token, activeTenant.tenant_id, {
        platform: selectedComment.platform,
        integration_type: selectedComment.integration_type || undefined,
        comment_id: selectedComment.id,
        account_id: values.account_id,
        content: values.content,
      });
      setSelectedComment(null);
      setSelectedDetail(null);
      replyForm.resetFields();
      await loadTabData();
      message.success("回复已提交");
    } catch (error) {
      message.error(error instanceof Error ? error.message : "发送回复失败");
    } finally {
      setLoading(false);
    }
  }

  const accountColumns = [
    {
      title: "平台",
      render: (_: unknown, record: PlatformAccount) => (
        <Space>
          <Tag>{record.platform}</Tag>
          {record.integration_type ? <Tag color="geekblue">{record.integration_type === "personal" ? "个人" : "企业"}</Tag> : null}
        </Space>
      ),
    },
    { title: "名称", dataIndex: "display_name" },
    { title: "外部ID", dataIndex: "external_id" },
    { title: "状态", dataIndex: "status", render: (value: string) => <Tag>{value}</Tag> },
    { title: "风险/风控", dataIndex: "risk_status", render: (value?: string | null) => value || "-" },
    { title: "Token到期", dataIndex: "access_token_expires_at", render: formatDateTime },
    { title: "最近校验", dataIndex: "last_validated_at", render: formatDateTime },
    { title: "最近错误", dataIndex: "last_error" },
    {
      title: "操作",
      render: (_: unknown, record: PlatformAccount) => (
        <Button size="small" onClick={() => onRefreshPlatformAccount(record)}>
          刷新
        </Button>
      ),
    },
  ];

  const targetColumns = [
    {
      title: "平台",
      render: (_: unknown, record: PlatformTarget) => (
        <Space>
          <Tag>{record.platform}</Tag>
          {record.integration_type ? <Tag color="geekblue">{record.integration_type === "personal" ? "个人" : "企业"}</Tag> : null}
        </Space>
      ),
    },
    { title: "标题", dataIndex: "title" },
    { title: "外部ID", dataIndex: "external_id" },
    { title: "状态", dataIndex: "status", render: (value: string) => <Tag>{value}</Tag> },
    { title: "轮询间隔", dataIndex: "poll_interval", render: (value: number) => `${value}s` },
    { title: "最近轮询", dataIndex: "last_polled_at", render: formatDateTime },
    {
      title: "操作",
      render: (_: unknown, record: PlatformTarget) => (
        <Button size="small" onClick={() => onPollPlatformTarget(record)}>
          立即同步
        </Button>
      ),
    },
  ];

  const replyColumns = [
    {
      title: "平台",
      render: (_: unknown, record: PlatformReplyAction) => (
        <Space>
          <Tag>{record.platform}</Tag>
          {record.integration_type ? <Tag color="geekblue">{record.integration_type === "personal" ? "个人" : "企业"}</Tag> : null}
        </Space>
      ),
    },
    { title: "评论ID", dataIndex: "comment_id" },
    { title: "账号ID", dataIndex: "account_id" },
    { title: "内容", dataIndex: "content", ellipsis: true },
    { title: "状态", dataIndex: "status", render: (value: string) => <Tag>{value}</Tag> },
    { title: "发送时间", dataIndex: "sent_at", render: formatDateTime },
    { title: "错误", dataIndex: "error_message" },
  ];

  return (
    <div>
      <PageHeader title="统一运营台" description="在同一套后台里同时运营 B站和抖音：接入账号、管理目标、处理评论、发送回复。" />
      <Alert
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
        message="旧的账号、目标、评论、回复页面已并入这里。B站保留二维码登录和草稿能力；抖音支持企业授权链路与个人登录/Cookie 导入链路。"
      />
      <Card style={{ marginBottom: 16 }}>
        <Space wrap>
          <Text type="secondary">平台</Text>
          <Select
            value={currentPlatform}
            style={{ width: 180 }}
            options={[
              { label: "全部平台", value: "all" },
              { label: "B站", value: "bilibili" },
              { label: "抖音", value: "douyin" },
            ]}
            onChange={(value) => updateQuery({ platform: value })}
          />
          {currentPlatform === "douyin" ? (
            <>
              <Text type="secondary">来源</Text>
              <Select
                value={integrationFilter}
                style={{ width: 180 }}
                options={[
                  { label: "全部来源", value: "all" },
                  { label: "企业抖音", value: "enterprise" },
                  { label: "个人抖音", value: "personal" },
                ]}
                onChange={(value: IntegrationFilter) => setIntegrationFilter(value)}
              />
            </>
          ) : null}
        </Space>
      </Card>
      <Tabs
        activeKey={currentTab}
        onChange={(value) => updateQuery({ tab: value })}
        items={[
          {
            key: "accounts",
            label: "账号",
            children: (
              <Card
                extra={
                  <Space wrap>
                    <Button onClick={onStartBiliQrLogin}>B站二维码登录</Button>
                    <Button onClick={() => setBiliCredentialOpen(true)}>B站导入凭证</Button>
                    <Button onClick={() => setDouyinAppOpen(true)}>抖音新增应用</Button>
                    <Button onClick={() => setDouyinOauthOpen(true)} disabled={douyinApps.length === 0}>
                      抖音OAuth授权
                    </Button>
                    <Button onClick={() => setDouyinTokenOpen(true)} disabled={douyinApps.length === 0}>
                      抖音导入Token
                    </Button>
                    <Button onClick={() => setDouyinCodeOpen(true)} disabled={douyinApps.length === 0}>
                      抖音导入Code
                    </Button>
                    <Button onClick={onStartDouyinPersonalLogin} disabled={currentPlatform === "bilibili"}>
                      抖音个人扫码登录
                    </Button>
                    <Button onClick={() => setDouyinPersonalCookieOpen(true)} disabled={currentPlatform === "bilibili"}>
                      抖音个人导入Cookie
                    </Button>
                  </Space>
                }
              >
                <Table rowKey={(record) => makeRowKey(record.platform, record.integration_type, record.id)} dataSource={opsAccounts} columns={accountColumns} />
              </Card>
            ),
          },
          {
            key: "targets",
            label: "目标",
            children: (
              <Card
                extra={
                  <Space wrap>
                    <Button onClick={() => setBiliTargetCreateOpen(true)} disabled={currentPlatform === "douyin"}>
                      B站手动添加
                    </Button>
                    <Button onClick={() => setBiliTargetImportOpen(true)} disabled={bilibiliAccounts.length === 0 || currentPlatform === "douyin"}>
                      B站导入稿件
                    </Button>
                    <Button onClick={() => setDouyinTargetOpen(true)} disabled={douyinAccounts.length === 0 || currentPlatform === "bilibili"}>
                      抖音企业目标
                    </Button>
                    <Button
                      onClick={() => setDouyinPersonalTargetOpen(true)}
                      disabled={douyinPersonalAccounts.length === 0 || currentPlatform === "bilibili"}
                    >
                      抖音个人目标
                    </Button>
                  </Space>
                }
              >
                <Table rowKey={(record) => makeRowKey(record.platform, record.integration_type, record.id)} dataSource={opsTargets} columns={targetColumns} />
              </Card>
            ),
          },
          {
            key: "inbox",
            label: "收件箱",
            children: (
              <Card
                extra={
                  <Space>
                    <Button
                      onClick={() =>
                        onMarkHandled(
                          selectedCommentKeys.map((key) => parseRowKey(key)),
                          true,
                        )
                      }
                    >
                      批量标记已处理
                    </Button>
                    <Button
                      onClick={() =>
                        onMarkHandled(
                          selectedCommentKeys.map((key) => parseRowKey(key)),
                          false,
                        )
                      }
                    >
                      恢复待处理
                    </Button>
                  </Space>
                }
              >
                <Space wrap style={{ marginBottom: 16 }}>
                  <Input
                    placeholder="搜索用户、评论内容或原始ID"
                    value={keyword}
                    onChange={(event) => setKeyword(event.target.value)}
                    style={{ width: 260 }}
                  />
                  <Select
                    value={handledFilter}
                    onChange={setHandledFilter}
                    style={{ width: 150 }}
                    options={[
                      { label: "全部处理状态", value: "all" },
                      { label: "待处理", value: "pending" },
                      { label: "已处理", value: "handled" },
                    ]}
                  />
                  <Select
                    value={repliedFilter}
                    onChange={setRepliedFilter}
                    style={{ width: 150 }}
                    options={[
                      { label: "全部回复状态", value: "all" },
                      { label: "未回复", value: "unreplied" },
                      { label: "已回复", value: "replied" },
                    ]}
                  />
                  <Select
                    value={typeFilter}
                    onChange={setTypeFilter}
                    style={{ width: 150 }}
                    options={[
                      { label: "全部评论类型", value: "all" },
                      { label: "主评论", value: "top" },
                      { label: "楼中楼/回复", value: "sub" },
                    ]}
                  />
                  <Select value={accountFilter} onChange={setAccountFilter} style={{ width: 220 }} options={accountOptions} />
                  <Select value={targetFilter} onChange={setTargetFilter} style={{ width: 220 }} options={targetOptions} />
                </Space>
                <Table
                  rowKey={(record) => makeRowKey(record.platform, record.integration_type, record.id)}
                  dataSource={opsComments}
                  rowSelection={{
                    selectedRowKeys: selectedCommentKeys,
                    onChange: setSelectedCommentKeys,
                  }}
                  onRow={(record) => ({ onClick: () => openCommentDetail(record) })}
                  columns={[
                    {
                      title: "平台",
                      render: (_: unknown, record: PlatformComment) => (
                        <Space>
                          <Tag>{record.platform}</Tag>
                          {record.integration_type ? (
                            <Tag color="geekblue">{record.integration_type === "personal" ? "个人" : "企业"}</Tag>
                          ) : null}
                        </Space>
                      ),
                    },
                    { title: "用户", dataIndex: "author_name" },
                    { title: "评论内容", dataIndex: "content", ellipsis: true },
                    { title: "点赞", dataIndex: "like_count" },
                    {
                      title: "类型",
                      render: (_: unknown, record: PlatformComment) => <Tag>{record.is_top_level ? "主评论" : "回复"}</Tag>,
                    },
                    {
                      title: "处理",
                      render: (_: unknown, record: PlatformComment) => (
                        <Tag color={record.is_handled ? "green" : "orange"}>{record.is_handled ? "已处理" : "待处理"}</Tag>
                      ),
                    },
                    {
                      title: "回复",
                      render: (_: unknown, record: PlatformComment) => (
                        <Tag color={record.is_replied ? "blue" : "default"}>{record.is_replied ? "已回复" : "未回复"}</Tag>
                      ),
                    },
                    { title: "发布时间", dataIndex: "posted_at", render: formatDateTime },
                  ]}
                />
              </Card>
            ),
          },
          {
            key: "replies",
            label: "回复记录",
            children: <Card><Table rowKey={(record) => makeRowKey(record.platform, record.integration_type, record.id)} dataSource={opsReplyActions} columns={replyColumns} /></Card>,
          },
        ]}
      />

      <Modal title="B站导入凭证" open={biliCredentialOpen} onCancel={() => setBiliCredentialOpen(false)} footer={null} destroyOnClose>
        <Form layout="vertical" form={biliCredentialForm} onFinish={onImportBiliCredentials}>
          <Form.Item label="SESSDATA" name="sessdata" rules={[{ required: true }]}><Input.TextArea rows={2} /></Form.Item>
          <Form.Item label="bili_jct" name="bili_jct" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item label="buvid3" name="buvid3"><Input /></Form.Item>
          <Form.Item label="buvid4" name="buvid4"><Input /></Form.Item>
          <Form.Item label="DedeUserID" name="dedeuserid"><Input /></Form.Item>
          <Form.Item label="ac_time_value" name="ac_time_value"><Input.TextArea rows={2} /></Form.Item>
          <Button type="primary" htmlType="submit" block loading={loading}>导入</Button>
        </Form>
      </Modal>

      <Modal title="扫码绑定B站账号" open={biliQrOpen} onCancel={() => setBiliQrOpen(false)} onOk={() => undefined} okButtonProps={{ style: { display: "none" } }}>
        {qrSession && (
          <Space direction="vertical" style={{ width: "100%" }}>
            <Image src={biliQrImageSrc} alt="QR code" width={240} preview={false} />
            <Paragraph copyable>{qrSession.login_url}</Paragraph>
            <Text type="secondary">状态：{qrStatus?.status || qrSession.status}</Text>
          </Space>
        )}
      </Modal>

      <Modal title="新增抖音应用" open={douyinAppOpen} onCancel={() => setDouyinAppOpen(false)} footer={null} destroyOnClose>
        <Form layout="vertical" form={douyinAppForm} onFinish={onCreateDouyinApp}>
          <Form.Item label="应用名称" name="name" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item label="Client Key" name="client_key" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item label="Client Secret" name="client_secret" rules={[{ required: true }]}><Input.Password /></Form.Item>
          <Button type="primary" htmlType="submit" block loading={loading}>保存</Button>
        </Form>
      </Modal>

      <Modal title="启动抖音OAuth授权" open={douyinOauthOpen} onCancel={() => setDouyinOauthOpen(false)} footer={null} destroyOnClose>
        <Form layout="vertical" form={douyinOauthForm} onFinish={onStartDouyinOauth}>
          <Form.Item label="选择应用" name="app_id" rules={[{ required: true }]}>
            <Select options={douyinApps.map((item) => ({ label: `${item.name} (${item.client_key})`, value: item.id }))} />
          </Form.Item>
          <Button type="primary" htmlType="submit" block>打开授权页</Button>
        </Form>
      </Modal>

      <Modal title="抖音导入Token" open={douyinTokenOpen} onCancel={() => setDouyinTokenOpen(false)} footer={null} destroyOnClose>
        <Form layout="vertical" form={douyinTokenForm} onFinish={onImportDouyinToken}>
          <Form.Item label="应用" name="app_id" rules={[{ required: true }]}>
            <Select options={douyinApps.map((item) => ({ label: `${item.name} (${item.client_key})`, value: item.id }))} />
          </Form.Item>
          <Form.Item label="Open ID" name="open_id" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item label="Access Token" name="access_token" rules={[{ required: true }]}><Input.TextArea rows={4} /></Form.Item>
          <Form.Item label="Refresh Token" name="refresh_token"><Input.TextArea rows={2} /></Form.Item>
          <Form.Item label="昵称" name="nickname"><Input /></Form.Item>
          <Form.Item label="头像链接" name="avatar_url"><Input /></Form.Item>
          <Button type="primary" htmlType="submit" block loading={loading}>导入</Button>
        </Form>
      </Modal>

      <Modal title="抖音导入授权Code" open={douyinCodeOpen} onCancel={() => setDouyinCodeOpen(false)} footer={null} destroyOnClose>
        <Form layout="vertical" form={douyinCodeForm} onFinish={onExchangeDouyinCode}>
          <Form.Item label="应用" name="app_id" rules={[{ required: true }]}>
            <Select options={douyinApps.map((item) => ({ label: `${item.name} (${item.client_key})`, value: item.id }))} />
          </Form.Item>
          <Form.Item label="授权 Code" name="code" rules={[{ required: true }]}><Input.TextArea rows={3} /></Form.Item>
          <Button type="primary" htmlType="submit" block loading={loading}>交换并导入</Button>
        </Form>
      </Modal>

      <Modal
        title="抖音个人扫码登录"
        open={douyinPersonalLoginOpen}
        onCancel={() => setDouyinPersonalLoginOpen(false)}
        onOk={() => undefined}
        okButtonProps={{ style: { display: "none" } }}
      >
        {douyinPersonalLoginSession && (
          <Space direction="vertical" style={{ width: "100%" }}>
            {douyinPersonalQrImageSrc ? (
              <Image src={douyinPersonalQrImageSrc} alt="Douyin personal QR code" width={240} preview={false} />
            ) : null}
            {douyinPersonalLoginSession.login_url ? <Paragraph copyable>{douyinPersonalLoginSession.login_url}</Paragraph> : null}
            <Text type="secondary">状态：{douyinPersonalLoginStatus?.status || douyinPersonalLoginSession.status}</Text>
            {douyinPersonalLoginStatus?.detail ? <Text type="danger">{douyinPersonalLoginStatus.detail}</Text> : null}
          </Space>
        )}
      </Modal>

      <Modal title="抖音个人导入 Cookie" open={douyinPersonalCookieOpen} onCancel={() => setDouyinPersonalCookieOpen(false)} footer={null} destroyOnClose>
        <Form layout="vertical" form={douyinPersonalCookieForm} onFinish={onImportDouyinPersonalCookie}>
          <Form.Item label="Cookie" name="cookie" rules={[{ required: true }]}><Input.TextArea rows={6} /></Form.Item>
          <Form.Item label="昵称" name="nickname"><Input /></Form.Item>
          <Form.Item label="头像链接" name="avatar_url"><Input /></Form.Item>
          <Form.Item label="用户ID" name="external_user_id"><Input /></Form.Item>
          <Button type="primary" htmlType="submit" block loading={loading}>导入</Button>
        </Form>
      </Modal>

      <Modal title="B站手动添加目标" open={biliTargetCreateOpen} onCancel={() => setBiliTargetCreateOpen(false)} footer={null} destroyOnClose>
        <Form layout="vertical" form={biliTargetCreateForm} onFinish={onCreateBiliTarget}>
          <Form.Item label="B站账号" name="account_id" rules={[{ required: true }]}>
            <Select options={bilibiliAccounts.map((item) => ({ label: `${item.username} (${item.uid})`, value: item.id }))} />
          </Form.Item>
          <Form.Item label="OID/AID" name="oid" rules={[{ required: true }]}><InputNumber style={{ width: "100%" }} /></Form.Item>
          <Form.Item label="BVID" name="bvid" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item label="标题" name="title" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item label="UP主MID" name="owner_mid"><InputNumber style={{ width: "100%" }} /></Form.Item>
          <Form.Item label="轮询间隔（秒）" name="poll_interval" initialValue={300}><InputNumber style={{ width: "100%" }} min={30} /></Form.Item>
          <Button type="primary" htmlType="submit" block loading={loading}>添加</Button>
        </Form>
      </Modal>

      <Modal title="B站导入稿件" open={biliTargetImportOpen} onCancel={() => setBiliTargetImportOpen(false)} footer={null} width={900} destroyOnClose>
        <Form layout="vertical" form={biliTargetImportForm} onFinish={onImportBiliTargets}>
          <Form.Item label="选择账号" name="account_id" rules={[{ required: true }]}>
            <Select
              options={bilibiliAccounts.map((item) => ({ label: `${item.username} (${item.uid})`, value: item.id }))}
              onChange={(value) => onLoadBiliImportPreview(String(value)).catch(console.error)}
            />
          </Form.Item>
          <Form.Item label="导入后的轮询间隔（秒）" name="poll_interval" initialValue={300}>
            <InputNumber style={{ width: "100%" }} min={30} />
          </Form.Item>
          <Table
            rowKey="bvid"
            pagination={false}
            dataSource={biliTargetCandidates}
            rowSelection={{
              selectedRowKeys: selectedCandidateKeys,
              onChange: setSelectedCandidateKeys,
              getCheckboxProps: (record) => ({ disabled: record.already_monitored }),
            }}
            columns={[
              { title: "标题", dataIndex: "title" },
              { title: "BVID", dataIndex: "bvid" },
              { title: "OID", dataIndex: "oid" },
              { title: "状态", render: (_, record) => <Tag>{record.already_monitored ? "已监控" : "可导入"}</Tag> },
            ]}
            style={{ marginBottom: 16 }}
          />
          <Button type="primary" htmlType="submit" block loading={loading} disabled={selectedCandidateKeys.length === 0}>
            导入已选稿件
          </Button>
        </Form>
      </Modal>

      <Modal title="新增抖音目标" open={douyinTargetOpen} onCancel={() => setDouyinTargetOpen(false)} footer={null} destroyOnClose>
        <Form layout="vertical" form={douyinTargetForm} onFinish={onCreateDouyinTarget}>
          <Form.Item label="抖音账号" name="account_id" rules={[{ required: true }]}>
            <Select options={douyinAccounts.map((item) => ({ label: `${item.nickname} (${item.open_id})`, value: item.id }))} />
          </Form.Item>
          <Form.Item label="Item ID" name="item_id" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item label="标题" name="title" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item label="轮询间隔（秒）" name="poll_interval" initialValue={300}><InputNumber style={{ width: "100%" }} min={30} /></Form.Item>
          <Button type="primary" htmlType="submit" block loading={loading}>添加</Button>
        </Form>
      </Modal>

      <Modal title="新增抖音个人目标" open={douyinPersonalTargetOpen} onCancel={() => setDouyinPersonalTargetOpen(false)} footer={null} destroyOnClose>
        <Form layout="vertical" form={douyinPersonalTargetForm} onFinish={onCreateDouyinPersonalTarget}>
          <Form.Item label="抖音个人账号" name="account_id" rules={[{ required: true }]}>
            <Select options={douyinPersonalAccounts.map((item) => ({ label: `${item.nickname} (${item.external_user_id})`, value: item.id }))} />
          </Form.Item>
          <Form.Item label="视频链接" name="video_url"><Input /></Form.Item>
          <Form.Item label="Aweme ID" name="aweme_id"><Input /></Form.Item>
          <Form.Item label="标题" name="title"><Input /></Form.Item>
          <Form.Item label="轮询间隔（秒）" name="poll_interval" initialValue={300}><InputNumber style={{ width: "100%" }} min={30} /></Form.Item>
          <Button type="primary" htmlType="submit" block loading={loading}>添加</Button>
        </Form>
      </Modal>

      <Drawer
        width={560}
        open={Boolean(selectedComment)}
        onClose={() => {
          setSelectedComment(null);
          setSelectedDetail(null);
        }}
        title={selectedComment ? `${selectedComment.author_name} 的评论` : ""}
      >
        {selectedComment && (
          <Spin spinning={detailLoading}>
            <Space direction="vertical" style={{ width: "100%" }}>
              <Space>
                <Tag>{selectedComment.platform}</Tag>
                {selectedComment.integration_type ? <Tag color="geekblue">{selectedComment.integration_type === "personal" ? "个人" : "企业"}</Tag> : null}
                <Tag>{selectedComment.is_top_level ? "主评论" : "回复"}</Tag>
              </Space>
              <div>
                <Text type="secondary">发布时间</Text>
                <Paragraph>{formatDateTime((selectedDetail ?? selectedComment).posted_at)}</Paragraph>
              </div>
              <div>
                <Text type="secondary">评论内容</Text>
                <Paragraph>{(selectedDetail ?? selectedComment).content}</Paragraph>
              </div>
              <div>
                <Text type="secondary">原始ID</Text>
                <Paragraph copyable>{(selectedDetail ?? selectedComment).external_id}</Paragraph>
              </div>
              <Space>
                <Button onClick={() => onMarkHandled([{ platform: selectedComment.platform, integration_type: selectedComment.integration_type || undefined, id: selectedComment.id }], !selectedComment.is_handled)}>
                  {selectedComment.is_handled ? "恢复待处理" : "标记已处理"}
                </Button>
              </Space>
              {selectedDetail && selectedDetail.events.length > 0 ? (
                <Card size="small" title="事件时间线">
                  <Space direction="vertical" style={{ width: "100%" }}>
                    {selectedDetail.events.map((event) => (
                      <div key={event.id}>
                        <Space>
                          <Tag>{event.event_type}</Tag>
                          <Text type="secondary">{formatDateTime(event.created_at)}</Text>
                        </Space>
                        <Paragraph style={{ marginBottom: 0 }}>{JSON.stringify(event.payload, null, 2)}</Paragraph>
                      </div>
                    ))}
                  </Space>
                </Card>
              ) : null}
              {selectedDetail && selectedDetail.reply_drafts.length > 0 ? (
                <Card size="small" title="草稿">
                  <Space direction="vertical" style={{ width: "100%" }}>
                    {selectedDetail.reply_drafts.map((draft) => (
                      <div key={draft.id}>
                        <Space>
                          <Tag>{draft.status}</Tag>
                          <Text type="secondary">{formatDateTime(draft.created_at)}</Text>
                          <Button size="small" onClick={() => replyForm.setFieldValue("content", draft.content)}>
                            使用草稿
                          </Button>
                        </Space>
                        <Paragraph style={{ marginBottom: 0 }}>{draft.content}</Paragraph>
                      </div>
                    ))}
                  </Space>
                </Card>
              ) : null}
              {selectedDetail ? (
                <Card size="small" title="历史回复">
                  <Space direction="vertical" style={{ width: "100%" }}>
                    {selectedDetail.reply_actions.length === 0 ? (
                      <Text type="secondary">暂无回复记录</Text>
                    ) : (
                      selectedDetail.reply_actions.map((action) => (
                        <div key={makeRowKey(action.platform, action.integration_type, action.id)}>
                          <Space>
                            <Tag>{action.status}</Tag>
                            <Text type="secondary">{formatDateTime(action.created_at)}</Text>
                          </Space>
                          <Paragraph style={{ marginBottom: 0 }}>{action.content || "已记录请求"}</Paragraph>
                        </div>
                      ))
                    )}
                  </Space>
                </Card>
              ) : null}
              {aiReplyStatus ? (
                <Card size="small" title="AI 回复助手">
                  <Space direction="vertical" style={{ width: "100%" }}>
                    <Text type="secondary">
                      {aiReplyStatus.enabled
                        ? `已启用 · ${aiReplyStatus.model} · ${aiReplyStatus.api_mode} · ${
                            aiReplyStatus.mode === "direct_send" ? "直接发送" : "人工审核"
                          }`
                        : "未启用 AI 回复，请先配置环境变量"}
                    </Text>
                    <Input.TextArea
                      rows={3}
                      placeholder="可选：补充语气、字数或业务要求"
                      value={aiInstruction}
                      onChange={(event) => setAiInstruction(event.target.value)}
                    />
                    <Button onClick={onGenerateAIReply} loading={aiLoading} disabled={!aiReplyStatus.enabled}>
                      {aiReplyStatus.mode === "direct_send" ? "AI 生成并发送" : "AI 生成建议稿"}
                    </Button>
                  </Space>
                </Card>
              ) : null}
              <Form layout="vertical" form={replyForm} onFinish={onSendReply}>
                <Form.Item label="回复账号" name="account_id" rules={[{ required: true }]}>
                  <Select options={platformScopedAccountOptions} />
                </Form.Item>
                <Form.Item label="回复内容" name="content" rules={[{ required: true }]}>
                  <Input.TextArea rows={5} />
                </Form.Item>
                <Space>
                  {selectedComment.platform === "bilibili" ? <Button onClick={onCreateDraft}>保存草稿</Button> : null}
                  <Button type="primary" htmlType="submit" loading={loading}>
                    发送回复
                  </Button>
                </Space>
              </Form>
            </Space>
          </Spin>
        )}
      </Drawer>
    </div>
  );
}
