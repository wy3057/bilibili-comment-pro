import { Card, Col, Row, Table } from "antd";
import { useEffect, useState } from "react";
import { fetchSystemMetrics, fetchTaskRuns } from "../api/endpoints";
import { MetricCard } from "../components/MetricCard";
import { PageHeader } from "../components/PageHeader";
import { useAuth } from "../store/auth";
import type { SystemMetrics, TaskRun } from "../types/api";
import { formatDateTime } from "../utils/format";
import { useTenantRealtime } from "../utils/realtime";

export function SystemPage() {
  const { token, activeTenant } = useAuth();
  const [metrics, setMetrics] = useState<SystemMetrics | null>(null);
  const [jobs, setJobs] = useState<TaskRun[]>([]);
  const realtimeVersion = useTenantRealtime(token, activeTenant?.tenant_id);

  useEffect(() => {
    async function load() {
      if (!token || !activeTenant) return;
      const [summary, runs] = await Promise.all([
        fetchSystemMetrics(token, activeTenant.tenant_id),
        fetchTaskRuns(token, activeTenant.tenant_id),
      ]);
      setMetrics(summary);
      setJobs(runs);
    }
    load().catch(console.error);
  }, [token, activeTenant, realtimeVersion]);

  return (
    <div>
      <PageHeader title="系统监控" description="从任务积压、失败率、登录失效到风险账号状态的统一观测页。" />
      <Row gutter={[16, 16]}>
        <Col xs={24} md={12} xl={8}>
          <MetricCard title="任务积压" value={metrics?.queue_backlog ?? "-"} />
        </Col>
        <Col xs={24} md={12} xl={8}>
          <MetricCard title="24h 失败任务" value={metrics?.failed_tasks_last_24h ?? "-"} />
        </Col>
        <Col xs={24} md={12} xl={8}>
          <MetricCard title="登录失效账号" value={metrics?.login_expired_accounts ?? "-"} />
        </Col>
        <Col xs={24} md={12} xl={8}>
          <MetricCard title="活跃目标" value={metrics?.active_targets ?? "-"} />
        </Col>
        <Col xs={24} md={12} xl={8}>
          <MetricCard title="风险账号" value={metrics?.risk_accounts ?? "-"} />
        </Col>
      </Row>
      <Card title="任务运行记录" style={{ marginTop: 24 }}>
        <Table
          rowKey="id"
          dataSource={jobs}
          columns={[
            { title: "任务名", dataIndex: "task_name" },
            { title: "类型", dataIndex: "task_kind" },
            { title: "状态", dataIndex: "status" },
            { title: "开始时间", dataIndex: "started_at", render: formatDateTime },
            { title: "结束时间", dataIndex: "finished_at", render: formatDateTime },
            { title: "错误", dataIndex: "error_message" },
          ]}
        />
      </Card>
    </div>
  );
}
