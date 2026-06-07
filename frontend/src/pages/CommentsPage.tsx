import { App, Button, Card, Drawer, Form, Input, Select, Space, Spin, Table, Tag, Typography } from "antd";
import { Key, useEffect, useMemo, useState } from "react";
import {
  createReplyDraft,
  fetchAccounts,
  fetchCommentDetail,
  fetchComments,
  markCommentsHandled,
  sendReply,
} from "../api/endpoints";
import { PageHeader } from "../components/PageHeader";
import { useAuth } from "../store/auth";
import type { BilibiliAccount, CommentDetail, CommentItem } from "../types/api";
import { formatDateTime } from "../utils/format";
import { useTenantRealtime } from "../utils/realtime";

const { Paragraph, Text } = Typography;

export function CommentsPage() {
  const { message } = App.useApp();
  const { token, activeTenant } = useAuth();
  const [items, setItems] = useState<CommentItem[]>([]);
  const [accounts, setAccounts] = useState<BilibiliAccount[]>([]);
  const [selected, setSelected] = useState<CommentItem | null>(null);
  const [selectedDetail, setSelectedDetail] = useState<CommentDetail | null>(null);
  const [selectedKeys, setSelectedKeys] = useState<Key[]>([]);
  const [detailLoading, setDetailLoading] = useState(false);
  const [keyword, setKeyword] = useState("");
  const [handledFilter, setHandledFilter] = useState<"all" | "handled" | "pending">("all");
  const [repliedFilter, setRepliedFilter] = useState<"all" | "replied" | "unreplied">("all");
  const [typeFilter, setTypeFilter] = useState<"all" | "top" | "sub">("all");
  const [accountFilter, setAccountFilter] = useState<string>("all");
  const [replyForm] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const realtimeVersion = useTenantRealtime(token, activeTenant?.tenant_id);

  async function refreshSelectedDetail(commentId: string) {
    if (!token || !activeTenant) return;
    const detail = await fetchCommentDetail(token, activeTenant.tenant_id, commentId);
    setSelectedDetail(detail);
  }

  async function loadData() {
    if (!token || !activeTenant) return;
    const [comments, accountRows] = await Promise.all([
      fetchComments(token, activeTenant.tenant_id),
      fetchAccounts(token, activeTenant.tenant_id),
    ]);
    setItems(comments);
    setAccounts(accountRows);
  }

  useEffect(() => {
    loadData().catch(console.error);
  }, [token, activeTenant, realtimeVersion]);

  const defaultAccountId = useMemo(() => accounts[0]?.id, [accounts]);

  useEffect(() => {
    if (defaultAccountId) {
      replyForm.setFieldValue("account_id", defaultAccountId);
    }
  }, [defaultAccountId, replyForm]);

  const filteredItems = useMemo(() => {
    const normalizedKeyword = keyword.trim().toLowerCase();
    return items.filter((item) => {
      if (handledFilter === "handled" && !item.is_handled) return false;
      if (handledFilter === "pending" && item.is_handled) return false;
      if (repliedFilter === "replied" && !item.is_replied) return false;
      if (repliedFilter === "unreplied" && item.is_replied) return false;
      if (typeFilter === "top" && !item.is_top_level) return false;
      if (typeFilter === "sub" && item.is_top_level) return false;
      if (accountFilter !== "all" && item.account_id !== accountFilter) return false;
      if (!normalizedKeyword) return true;
      return (
        item.member_name.toLowerCase().includes(normalizedKeyword) ||
        item.message.toLowerCase().includes(normalizedKeyword) ||
        String(item.rpid).includes(normalizedKeyword)
      );
    });
  }, [accountFilter, handledFilter, items, keyword, repliedFilter, typeFilter]);

  async function openDetail(record: CommentItem) {
    if (!token || !activeTenant) return;
    setSelected(record);
    setSelectedDetail(null);
    setDetailLoading(true);
    try {
      const detail = await fetchCommentDetail(token, activeTenant.tenant_id, record.id);
      setSelectedDetail(detail);
      replyForm.setFieldValue("account_id", detail.account_id || defaultAccountId);
    } catch (error) {
      message.error(error instanceof Error ? error.message : "加载评论详情失败");
    } finally {
      setDetailLoading(false);
    }
  }

  async function onMarkHandled(commentIds: string[], isHandled: boolean) {
    if (!token || !activeTenant || commentIds.length === 0) return;
    try {
      await markCommentsHandled(token, activeTenant.tenant_id, {
        comment_ids: commentIds,
        is_handled: isHandled,
      });
      if (selected && commentIds.includes(selected.id)) {
        setSelected({ ...selected, is_handled: isHandled });
      }
      if (selectedDetail && commentIds.includes(selectedDetail.id)) {
        setSelectedDetail({ ...selectedDetail, is_handled: isHandled });
      }
      setSelectedKeys([]);
      await loadData();
      message.success("处理状态已更新");
    } catch (error) {
      message.error(error instanceof Error ? error.message : "更新失败");
    }
  }

  async function onCreateDraft() {
    const content = replyForm.getFieldValue("content");
    if (!token || !activeTenant || !selected || !content) return;
    try {
      await createReplyDraft(token, activeTenant.tenant_id, {
        comment_id: selected.id,
        content,
      });
      await refreshSelectedDetail(selected.id);
      message.success("草稿已创建");
    } catch (error) {
      message.error(error instanceof Error ? error.message : "创建草稿失败");
    }
  }

  async function onSendReply(values: { account_id: string; content: string }) {
    if (!token || !activeTenant || !selected) return;
    setLoading(true);
    try {
      await sendReply(token, activeTenant.tenant_id, {
        comment_id: selected.id,
        account_id: values.account_id,
        content: values.content,
      });
      replyForm.resetFields();
      setSelected(null);
      setSelectedDetail(null);
      await loadData();
      message.success("回复已提交");
    } catch (error) {
      message.error(error instanceof Error ? error.message : "发送回复失败");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <PageHeader title="评论工作台" description="查看新评论、上下文与处理状态，并为人工回复预留操作入口。" />
      <Card
        extra={
          <Space>
            <Button onClick={() => onMarkHandled(selectedKeys as string[], true)}>批量标记已处理</Button>
            <Button onClick={() => onMarkHandled(selectedKeys as string[], false)}>恢复待处理</Button>
          </Space>
        }
      >
        <Space wrap style={{ marginBottom: 16 }}>
          <Input
            placeholder="搜索用户、评论内容或 RPID"
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
              { label: "楼中楼", value: "sub" },
            ]}
          />
          <Select
            value={accountFilter}
            onChange={setAccountFilter}
            style={{ width: 220 }}
            options={[
              { label: "全部 B 站账号", value: "all" },
              ...accounts.map((item) => ({ label: `${item.username} (${item.uid})`, value: item.id })),
            ]}
          />
        </Space>
        <Table
          rowKey="id"
          dataSource={filteredItems}
          rowSelection={{
            selectedRowKeys: selectedKeys,
            onChange: setSelectedKeys,
          }}
          onRow={(record) => ({ onClick: () => openDetail(record) })}
          columns={[
            { title: "用户", dataIndex: "member_name" },
            { title: "评论内容", dataIndex: "message", ellipsis: true },
            { title: "点赞", dataIndex: "like_count" },
            {
              title: "类型",
              render: (_, record) => <Tag>{record.is_top_level ? "主评论" : "楼中楼"}</Tag>,
            },
            {
              title: "处理",
              render: (_, record) => (
                <Tag color={record.is_handled ? "green" : "orange"}>{record.is_handled ? "已处理" : "待处理"}</Tag>
              ),
            },
            {
              title: "回复",
              render: (_, record) => (
                <Tag color={record.is_replied ? "blue" : "default"}>{record.is_replied ? "已回复" : "未回复"}</Tag>
              ),
            },
            { title: "发布时间", dataIndex: "posted_at", render: formatDateTime },
          ]}
        />
      </Card>
      <Drawer
        width={520}
        open={Boolean(selected)}
        onClose={() => {
          setSelected(null);
          setSelectedDetail(null);
        }}
        title={selected ? `${selected.member_name} 的评论` : ""}
      >
        {selected && (
          <Spin spinning={detailLoading}>
          <Space direction="vertical" style={{ width: "100%" }}>
            <div>
              <Text type="secondary">评论时间</Text>
              <Paragraph>{formatDateTime((selectedDetail ?? selected).posted_at)}</Paragraph>
            </div>
            <div>
              <Text type="secondary">评论内容</Text>
              <Paragraph>{(selectedDetail ?? selected).message}</Paragraph>
            </div>
            <div>
              <Text type="secondary">原始标识</Text>
              <Paragraph copyable>{(selectedDetail ?? selected).rpid}</Paragraph>
            </div>
            <Button onClick={() => onMarkHandled([selected.id], !selected.is_handled)}>
              {selected.is_handled ? "恢复待处理" : "标记已处理"}
            </Button>
            {selectedDetail && (
              <Card size="small" title="事件时间线">
                <Space direction="vertical" style={{ width: "100%" }}>
                  {selectedDetail.events.length === 0 ? (
                    <Text type="secondary">暂无事件</Text>
                  ) : (
                    selectedDetail.events.map((event) => (
                      <div key={event.id}>
                        <Space>
                          <Tag color={event.event_type === "updated" ? "blue" : "green"}>{event.event_type}</Tag>
                          <Text type="secondary">{formatDateTime(event.created_at)}</Text>
                        </Space>
                        <Paragraph style={{ marginBottom: 0 }}>
                          {JSON.stringify(event.payload, null, 2)}
                        </Paragraph>
                      </div>
                    ))
                  )}
                </Space>
              </Card>
            )}
            {selectedDetail && (
              <Card size="small" title="已保存草稿">
                <Space direction="vertical" style={{ width: "100%" }}>
                  {selectedDetail.reply_drafts.length === 0 ? (
                    <Text type="secondary">暂无草稿</Text>
                  ) : (
                    selectedDetail.reply_drafts.map((draft) => (
                      <div key={draft.id}>
                        <Space>
                          <Tag color={draft.status === "sent" ? "green" : "gold"}>{draft.status}</Tag>
                          <Text type="secondary">{formatDateTime(draft.created_at)}</Text>
                          <Button
                            size="small"
                            onClick={() => replyForm.setFieldValue("content", draft.content)}
                          >
                            使用草稿
                          </Button>
                        </Space>
                        <Paragraph style={{ marginBottom: 0 }}>{draft.content}</Paragraph>
                      </div>
                    ))
                  )}
                </Space>
              </Card>
            )}
            {selectedDetail && (
              <Card size="small" title="历史回复">
                <Space direction="vertical" style={{ width: "100%" }}>
                  {selectedDetail.reply_actions.length === 0 ? (
                    <Text type="secondary">暂无回复记录</Text>
                  ) : (
                    selectedDetail.reply_actions.map((action) => (
                      <div key={action.id}>
                        <Space>
                          <Tag color={action.status === "sent" ? "green" : action.status === "failed" ? "red" : "gold"}>
                            {action.status}
                          </Tag>
                          <Text type="secondary">{formatDateTime(action.created_at)}</Text>
                        </Space>
                        <Paragraph style={{ marginBottom: 0 }}>
                          {action.request_payload["content"]
                            ? `内容：${String(action.request_payload["content"])}`
                            : "已记录请求"}
                        </Paragraph>
                        {action.error_message ? <Text type="danger">{action.error_message}</Text> : null}
                      </div>
                    ))
                  )}
                </Space>
              </Card>
            )}
            <Form layout="vertical" form={replyForm} onFinish={onSendReply}>
              <Form.Item label="回复账号" name="account_id" rules={[{ required: true }]}>
                <Select
                  options={accounts.map((item) => ({ label: `${item.username} (${item.uid})`, value: item.id }))}
                />
              </Form.Item>
              <Form.Item label="回复内容" name="content" rules={[{ required: true }]}>
                <Input.TextArea rows={5} />
              </Form.Item>
              <Space>
                <Button onClick={onCreateDraft}>保存草稿</Button>
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
