import {
  Alert,
  App,
  Button,
  Card,
  Drawer,
  Form,
  Input,
  InputNumber,
  Modal,
  Select,
  Space,
  Table,
  Tag,
  Typography,
} from "antd";
import { useEffect, useMemo, useState } from "react";
import {
  createDouyinApp,
  createDouyinTarget,
  fetchDouyinAccounts,
  fetchDouyinApps,
  fetchDouyinComments,
  fetchDouyinReplyActions,
  fetchDouyinTargets,
  importDouyinAuthorization,
  markDouyinCommentsHandled,
  pollDouyinTarget,
  refreshDouyinAccount,
  sendDouyinReply,
} from "../api/endpoints";
import { PageHeader } from "../components/PageHeader";
import { useAuth } from "../store/auth";
import type {
  DouyinAccount,
  DouyinApp,
  DouyinCommentItem,
  DouyinReplyAction,
  DouyinTarget,
} from "../types/api";
import { formatDateTime } from "../utils/format";
import { useTenantRealtime } from "../utils/realtime";

const { Paragraph, Text } = Typography;

type AppFormValues = {
  name: string;
  client_key: string;
  client_secret: string;
};

type AuthFormValues = {
  app_id: string;
  open_id: string;
  access_token: string;
  refresh_token?: string;
  nickname?: string;
  avatar_url?: string;
};

type TargetFormValues = {
  account_id: string;
  item_id: string;
  title: string;
  poll_interval?: number;
};

type ReplyFormValues = {
  account_id: string;
  content: string;
};

export function DouyinPage() {
  const { message } = App.useApp();
  const { token, activeTenant } = useAuth();
  const [apps, setApps] = useState<DouyinApp[]>([]);
  const [accounts, setAccounts] = useState<DouyinAccount[]>([]);
  const [targets, setTargets] = useState<DouyinTarget[]>([]);
  const [comments, setComments] = useState<DouyinCommentItem[]>([]);
  const [replyActions, setReplyActions] = useState<DouyinReplyAction[]>([]);
  const [targetFilter, setTargetFilter] = useState<string>("all");
  const [selectedComment, setSelectedComment] = useState<DouyinCommentItem | null>(null);
  const [appOpen, setAppOpen] = useState(false);
  const [authOpen, setAuthOpen] = useState(false);
  const [targetOpen, setTargetOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [appForm] = Form.useForm<AppFormValues>();
  const [authForm] = Form.useForm<AuthFormValues>();
  const [targetForm] = Form.useForm<TargetFormValues>();
  const [replyForm] = Form.useForm<ReplyFormValues>();
  const realtimeVersion = useTenantRealtime(token, activeTenant?.tenant_id);

  async function loadMeta() {
    if (!token || !activeTenant) return;
    const [appRows, accountRows, targetRows, replyRows] = await Promise.all([
      fetchDouyinApps(token, activeTenant.tenant_id),
      fetchDouyinAccounts(token, activeTenant.tenant_id),
      fetchDouyinTargets(token, activeTenant.tenant_id),
      fetchDouyinReplyActions(token, activeTenant.tenant_id),
    ]);
    setApps(appRows);
    setAccounts(accountRows);
    setTargets(targetRows);
    setReplyActions(replyRows);
  }

  async function loadComments() {
    if (!token || !activeTenant) return;
    const rows = await fetchDouyinComments(token, activeTenant.tenant_id, {
      target_id: targetFilter === "all" ? undefined : targetFilter,
    });
    setComments(rows);
  }

  useEffect(() => {
    loadMeta().catch(console.error);
  }, [token, activeTenant, realtimeVersion]);

  useEffect(() => {
    loadComments().catch(console.error);
  }, [token, activeTenant, targetFilter, realtimeVersion]);

  const defaultAccountId = useMemo(() => accounts[0]?.id, [accounts]);

  useEffect(() => {
    if (defaultAccountId) {
      replyForm.setFieldValue("account_id", defaultAccountId);
    }
  }, [defaultAccountId, replyForm]);

  async function onCreateApp(values: AppFormValues) {
    if (!token || !activeTenant) return;
    setLoading(true);
    try {
      await createDouyinApp(token, activeTenant.tenant_id, values);
      setAppOpen(false);
      appForm.resetFields();
      await loadMeta();
      message.success("抖音应用配置已保存");
    } catch (error) {
      message.error(error instanceof Error ? error.message : "保存抖音应用失败");
    } finally {
      setLoading(false);
    }
  }

  async function onImportAuthorization(values: AuthFormValues) {
    if (!token || !activeTenant) return;
    setLoading(true);
    try {
      await importDouyinAuthorization(token, activeTenant.tenant_id, values);
      setAuthOpen(false);
      authForm.resetFields();
      await loadMeta();
      message.success("抖音授权账号已导入");
    } catch (error) {
      message.error(error instanceof Error ? error.message : "导入抖音授权失败");
    } finally {
      setLoading(false);
    }
  }

  async function onRefreshAuthorization(accountId: string) {
    if (!token || !activeTenant) return;
    setLoading(true);
    try {
      await refreshDouyinAccount(token, activeTenant.tenant_id, accountId);
      await loadMeta();
      message.success("抖音授权已刷新");
    } catch (error) {
      message.error(error instanceof Error ? error.message : "刷新抖音授权失败");
    } finally {
      setLoading(false);
    }
  }

  async function onCreateTarget(values: TargetFormValues) {
    if (!token || !activeTenant) return;
    setLoading(true);
    try {
      await createDouyinTarget(token, activeTenant.tenant_id, {
        ...values,
        poll_interval: values.poll_interval || 300,
      });
      setTargetOpen(false);
      targetForm.resetFields();
      await loadMeta();
      message.success("抖音监控目标已添加");
    } catch (error) {
      message.error(error instanceof Error ? error.message : "添加抖音目标失败");
    } finally {
      setLoading(false);
    }
  }

  async function onPollTarget(targetId: string) {
    if (!token || !activeTenant) return;
    try {
      const result = await pollDouyinTarget(token, activeTenant.tenant_id, targetId);
      await loadComments();
      await loadMeta();
      message.success(`抖音评论同步完成：新增 ${result.created} 条`);
    } catch (error) {
      message.error(error instanceof Error ? error.message : "同步抖音评论失败");
    }
  }

  async function onMarkHandled(commentIds: string[], isHandled: boolean) {
    if (!token || !activeTenant || commentIds.length === 0) return;
    try {
      await markDouyinCommentsHandled(token, activeTenant.tenant_id, {
        comment_ids: commentIds,
        is_handled: isHandled,
      });
      await loadComments();
      message.success("抖音评论处理状态已更新");
    } catch (error) {
      message.error(error instanceof Error ? error.message : "更新抖音评论状态失败");
    }
  }

  async function onSendReply(values: ReplyFormValues) {
    if (!token || !activeTenant || !selectedComment) return;
    setLoading(true);
    try {
      await sendDouyinReply(token, activeTenant.tenant_id, {
        comment_id: selectedComment.id,
        account_id: values.account_id,
        content: values.content,
      });
      replyForm.resetFields();
      setSelectedComment(null);
      await loadComments();
      await loadMeta();
      message.success("抖音评论回复已提交");
    } catch (error) {
      message.error(error instanceof Error ? error.message : "发送抖音回复失败");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <PageHeader title="抖音平台" description="以独立模块接入抖音开放平台，先支持应用配置、授权导入、评论同步和人工回复。" />
      <Alert
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
        message="当前管理后台是 Web 应用，不能直接发起抖音小程序的授权弹窗。请先通过你自己的抖音小程序完成官方授权，再把 open_id 和 access_token 导入到这里。"
      />
      <Card
        title="抖音应用配置"
        extra={
          <Button type="primary" onClick={() => setAppOpen(true)}>
            新增应用
          </Button>
        }
      >
        <Table
          rowKey="id"
          dataSource={apps}
          pagination={false}
          columns={[
            { title: "名称", dataIndex: "name" },
            { title: "Client Key", dataIndex: "client_key" },
            { title: "启用", dataIndex: "is_active", render: (value: boolean) => (value ? "是" : "否") },
            { title: "创建时间", dataIndex: "created_at", render: formatDateTime },
          ]}
        />
      </Card>
      <Card
        title="授权账号"
        style={{ marginTop: 16 }}
        extra={
          <Button onClick={() => setAuthOpen(true)} disabled={apps.length === 0}>
            导入授权
          </Button>
        }
      >
        <Table
          rowKey="id"
          dataSource={accounts}
          pagination={false}
          columns={[
            { title: "昵称", dataIndex: "nickname" },
            { title: "Open ID", dataIndex: "open_id" },
            { title: "状态", dataIndex: "status", render: (value: string) => <Tag>{value}</Tag> },
            { title: "到期时间", dataIndex: "access_token_expires_at", render: formatDateTime },
            { title: "最近校验", dataIndex: "last_validated_at", render: formatDateTime },
            { title: "最近错误", dataIndex: "last_error" },
            {
              title: "操作",
              render: (_, record: DouyinAccount) => (
                <Button size="small" onClick={() => onRefreshAuthorization(record.id)}>
                  刷新授权
                </Button>
              ),
            },
          ]}
        />
      </Card>
      <Card
        title="监控目标"
        style={{ marginTop: 16 }}
        extra={
          <Button onClick={() => setTargetOpen(true)} disabled={accounts.length === 0}>
            新增目标
          </Button>
        }
      >
        <Table
          rowKey="id"
          dataSource={targets}
          pagination={false}
          columns={[
            { title: "标题", dataIndex: "title" },
            { title: "Item ID", dataIndex: "item_id" },
            { title: "轮询间隔", dataIndex: "poll_interval", render: (value: number) => `${value}s` },
            { title: "最近轮询", dataIndex: "last_polled_at", render: formatDateTime },
            {
              title: "操作",
              render: (_, record: DouyinTarget) => (
                <Button size="small" onClick={() => onPollTarget(record.id)}>
                  立即同步
                </Button>
              ),
            },
          ]}
        />
      </Card>
      <Card
        title="评论工作台"
        style={{ marginTop: 16 }}
        extra={
          <Space>
            <Select
              value={targetFilter}
              onChange={setTargetFilter}
              style={{ width: 240 }}
              options={[
                { label: "全部抖音目标", value: "all" },
                ...targets.map((item) => ({ label: `${item.title} (${item.item_id})`, value: item.id })),
              ]}
            />
          </Space>
        }
      >
        <Table
          rowKey="id"
          dataSource={comments}
          onRow={(record) => ({ onClick: () => setSelectedComment(record) })}
          columns={[
            { title: "用户", dataIndex: "user_nickname" },
            { title: "评论内容", dataIndex: "content", ellipsis: true },
            { title: "点赞", dataIndex: "digg_count" },
            {
              title: "类型",
              render: (_, record: DouyinCommentItem) => <Tag>{record.is_top_level ? "主评论" : "回复"}</Tag>,
            },
            {
              title: "处理",
              render: (_, record: DouyinCommentItem) => (
                <Tag color={record.is_handled ? "green" : "orange"}>{record.is_handled ? "已处理" : "待处理"}</Tag>
              ),
            },
            {
              title: "回复",
              render: (_, record: DouyinCommentItem) => (
                <Tag color={record.is_replied ? "blue" : "default"}>{record.is_replied ? "已回复" : "未回复"}</Tag>
              ),
            },
            { title: "发布时间", dataIndex: "posted_at", render: formatDateTime },
          ]}
        />
      </Card>
      <Card title="回复记录" style={{ marginTop: 16 }}>
        <Table
          rowKey="id"
          dataSource={replyActions}
          pagination={false}
          columns={[
            { title: "评论ID", dataIndex: "comment_id" },
            { title: "状态", dataIndex: "status", render: (value: string) => <Tag>{value}</Tag> },
            { title: "发送时间", dataIndex: "sent_at", render: formatDateTime },
            { title: "错误", dataIndex: "error_message" },
          ]}
        />
      </Card>

      <Modal title="新增抖音应用" open={appOpen} onCancel={() => setAppOpen(false)} footer={null} destroyOnClose>
        <Form layout="vertical" form={appForm} onFinish={onCreateApp}>
          <Form.Item label="应用名称" name="name" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item label="Client Key" name="client_key" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item label="Client Secret" name="client_secret" rules={[{ required: true }]}>
            <Input.Password />
          </Form.Item>
          <Button type="primary" htmlType="submit" block loading={loading}>
            保存应用
          </Button>
        </Form>
      </Modal>

      <Modal
        title="导入抖音授权"
        open={authOpen}
        onCancel={() => setAuthOpen(false)}
        footer={null}
        destroyOnClose
      >
        <Form layout="vertical" form={authForm} onFinish={onImportAuthorization}>
          <Form.Item label="所属应用" name="app_id" rules={[{ required: true }]}>
            <Select options={apps.map((item) => ({ label: `${item.name} (${item.client_key})`, value: item.id }))} />
          </Form.Item>
          <Form.Item label="Open ID" name="open_id" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item label="Access Token" name="access_token" rules={[{ required: true }]}>
            <Input.TextArea rows={4} />
          </Form.Item>
          <Form.Item label="Refresh Token" name="refresh_token">
            <Input.TextArea rows={2} />
          </Form.Item>
          <Form.Item label="昵称" name="nickname">
            <Input />
          </Form.Item>
          <Form.Item label="头像链接" name="avatar_url">
            <Input />
          </Form.Item>
          <Button type="primary" htmlType="submit" block loading={loading}>
            导入授权
          </Button>
        </Form>
      </Modal>

      <Modal title="新增抖音监控目标" open={targetOpen} onCancel={() => setTargetOpen(false)} footer={null} destroyOnClose>
        <Form layout="vertical" form={targetForm} onFinish={onCreateTarget}>
          <Form.Item label="授权账号" name="account_id" rules={[{ required: true }]}>
            <Select
              options={accounts.map((item) => ({ label: `${item.nickname} (${item.open_id})`, value: item.id }))}
            />
          </Form.Item>
          <Form.Item label="Item ID" name="item_id" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item label="标题" name="title" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item label="轮询间隔（秒）" name="poll_interval" initialValue={300}>
            <InputNumber style={{ width: "100%" }} min={30} />
          </Form.Item>
          <Button type="primary" htmlType="submit" block loading={loading}>
            添加目标
          </Button>
        </Form>
      </Modal>

      <Drawer
        width={520}
        open={Boolean(selectedComment)}
        onClose={() => setSelectedComment(null)}
        title={selectedComment ? `${selectedComment.user_nickname} 的抖音评论` : ""}
      >
        {selectedComment && (
          <Space direction="vertical" style={{ width: "100%" }}>
            <div>
              <Text type="secondary">评论时间</Text>
              <Paragraph>{formatDateTime(selectedComment.posted_at)}</Paragraph>
            </div>
            <div>
              <Text type="secondary">评论内容</Text>
              <Paragraph>{selectedComment.content}</Paragraph>
            </div>
            <div>
              <Text type="secondary">原始评论 ID</Text>
              <Paragraph copyable>{selectedComment.comment_id}</Paragraph>
            </div>
            <Space>
              <Button onClick={() => onMarkHandled([selectedComment.id], !selectedComment.is_handled)}>
                {selectedComment.is_handled ? "恢复待处理" : "标记已处理"}
              </Button>
            </Space>
            <Form layout="vertical" form={replyForm} onFinish={onSendReply}>
              <Form.Item label="回复账号" name="account_id" rules={[{ required: true }]}>
                <Select
                  options={accounts.map((item) => ({ label: `${item.nickname} (${item.open_id})`, value: item.id }))}
                />
              </Form.Item>
              <Form.Item label="回复内容" name="content" rules={[{ required: true }]}>
                <Input.TextArea rows={5} />
              </Form.Item>
              <Button type="primary" htmlType="submit" block loading={loading}>
                发送回复
              </Button>
            </Form>
          </Space>
        )}
      </Drawer>
    </div>
  );
}
