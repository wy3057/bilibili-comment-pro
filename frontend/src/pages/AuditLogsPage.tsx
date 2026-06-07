import { Card, Table } from "antd";
import { useEffect, useState } from "react";
import { fetchAuditLogs } from "../api/endpoints";
import { PageHeader } from "../components/PageHeader";
import { useAuth } from "../store/auth";
import type { AuditLog } from "../types/api";
import { formatDateTime } from "../utils/format";
import { useTenantRealtime } from "../utils/realtime";

export function AuditLogsPage() {
  const { token, activeTenant } = useAuth();
  const [items, setItems] = useState<AuditLog[]>([]);
  const realtimeVersion = useTenantRealtime(token, activeTenant?.tenant_id);

  useEffect(() => {
    async function load() {
      if (!token || !activeTenant) return;
      setItems(await fetchAuditLogs(token, activeTenant.tenant_id));
    }
    load().catch(console.error);
  }, [token, activeTenant, realtimeVersion]);

  return (
    <div>
      <PageHeader title="审计日志" description="追踪绑定账号、发送回复、成员修改和系统登录等关键操作。" />
      <Card>
        <Table
          rowKey="id"
          dataSource={items}
          columns={[
            { title: "动作", dataIndex: "action" },
            { title: "操作人", dataIndex: "user_id", render: (value?: string | null) => value || "-" },
            { title: "实体", dataIndex: "entity_type" },
            { title: "实体ID", dataIndex: "entity_id" },
            {
              title: "载荷",
              dataIndex: "payload",
              render: (value: Record<string, unknown>) => (
                <pre style={{ margin: 0, whiteSpace: "pre-wrap", wordBreak: "break-word" }}>
                  {JSON.stringify(value, null, 2)}
                </pre>
              ),
            },
            { title: "时间", dataIndex: "created_at", render: formatDateTime },
          ]}
        />
      </Card>
    </div>
  );
}
