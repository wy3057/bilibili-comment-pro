import { Card, Table, Tag } from "antd";
import { useEffect, useState } from "react";
import { fetchReplyActions } from "../api/endpoints";
import { PageHeader } from "../components/PageHeader";
import { useAuth } from "../store/auth";
import type { ReplyAction } from "../types/api";
import { formatDateTime } from "../utils/format";
import { useTenantRealtime } from "../utils/realtime";

export function RepliesPage() {
  const { token, activeTenant } = useAuth();
  const [items, setItems] = useState<ReplyAction[]>([]);
  const realtimeVersion = useTenantRealtime(token, activeTenant?.tenant_id);

  useEffect(() => {
    async function load() {
      if (!token || !activeTenant) return;
      setItems(await fetchReplyActions(token, activeTenant.tenant_id));
    }
    load().catch(console.error);
  }, [token, activeTenant, realtimeVersion]);

  return (
    <div>
      <PageHeader title="回复记录" description="追踪人工回复的发送状态、请求载荷与失败原因。" />
      <Card>
        <Table
          rowKey="id"
          dataSource={items}
          columns={[
            { title: "评论ID", dataIndex: "comment_id" },
            { title: "账号", dataIndex: "account_id" },
            {
              title: "状态",
              dataIndex: "status",
              render: (value: string) => (
                <Tag color={value === "sent" ? "green" : value === "failed" ? "red" : "gold"}>{value}</Tag>
              ),
            },
            { title: "发送时间", dataIndex: "sent_at", render: formatDateTime },
            { title: "错误", dataIndex: "error_message" },
          ]}
        />
      </Card>
    </div>
  );
}
