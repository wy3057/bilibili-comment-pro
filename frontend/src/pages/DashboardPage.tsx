import { Card, Col, Empty, Row, Space, Table } from "antd";
import { useEffect, useState } from "react";
import { fetchOverview, fetchTaskRuns } from "../api/endpoints";
import { MetricCard } from "../components/MetricCard";
import { PageHeader } from "../components/PageHeader";
import { useAuth } from "../store/auth";
import type { OverviewStats, TaskRun } from "../types/api";
import { formatDateTime } from "../utils/format";
import { useTenantRealtime } from "../utils/realtime";

export function DashboardPage() {
  const { token, activeTenant } = useAuth();
  const [overview, setOverview] = useState<OverviewStats | null>(null);
  const [tasks, setTasks] = useState<TaskRun[]>([]);
  const realtimeVersion = useTenantRealtime(token, activeTenant?.tenant_id);

  useEffect(() => {
    async function load() {
      if (!token || !activeTenant) return;
      const [overviewData, tasksData] = await Promise.all([
        fetchOverview(token, activeTenant.tenant_id),
        fetchTaskRuns(token, activeTenant.tenant_id),
      ]);
      setOverview(overviewData);
      setTasks(tasksData.slice(0, 6));
    }
    load().catch(console.error);
  }, [token, activeTenant, realtimeVersion]);

  return (
    <div>
      <PageHeader title="总览仪表盘" description="从评论发现、回复执行到账号与任务状态的统一观察面板。" />
      <Row gutter={[16, 16]}>
        <Col xs={24} md={12} xl={8}>
          <MetricCard title="累计评论" value={overview?.total_comments ?? "-"} />
        </Col>
        <Col xs={24} md={12} xl={8}>
          <MetricCard title="待处理评论" value={overview?.pending_comments ?? "-"} />
        </Col>
        <Col xs={24} md={12} xl={8}>
          <MetricCard title="已回复评论" value={overview?.replied_comments ?? "-"} />
        </Col>
        <Col xs={24} md={12} xl={8}>
          <MetricCard title="监控目标" value={overview?.total_targets ?? "-"} />
        </Col>
        <Col xs={24} md={12} xl={8}>
          <MetricCard title="接入账号" value={overview?.total_accounts ?? "-"} />
        </Col>
        <Col xs={24} md={12} xl={8}>
          <MetricCard title="失败任务" value={overview?.failed_tasks ?? "-"} />
        </Col>
        <Col xs={24} md={12} xl={8}>
          <MetricCard title="回复率" value={overview ? `${overview.reply_rate}%` : "-"} />
        </Col>
        <Col xs={24} md={12} xl={8}>
          <MetricCard
            title="平均响应时长"
            value={
              overview?.avg_response_minutes != null ? `${overview.avg_response_minutes} 分钟` : "-"
            }
          />
        </Col>
      </Row>
      <Card style={{ marginTop: 24 }}>
        <Space direction="vertical" size="middle" style={{ width: "100%" }}>
          <PageHeader title="平台分布" description="对比 B站和抖音两条业务线的账号、目标和评论规模。" />
          <Table
            rowKey="platform"
            dataSource={overview?.platform_overview || []}
            pagination={false}
            columns={[
              { title: "平台", dataIndex: "platform" },
              { title: "账号数", dataIndex: "accounts" },
              { title: "目标数", dataIndex: "targets" },
              { title: "评论数", dataIndex: "comments" },
              { title: "待处理", dataIndex: "pending_comments" },
              { title: "已回复", dataIndex: "replied_comments" },
            ]}
          />
        </Space>
      </Card>
      <Card style={{ marginTop: 24 }}>
        <Space direction="vertical" size="middle" style={{ width: "100%" }}>
          <PageHeader title="最近任务" description="观察轮询、刷新凭证与同步任务的最新运行情况。" />
          <Table
            rowKey="id"
            dataSource={tasks}
            locale={{ emptyText: <Empty description="暂无任务数据" /> }}
            pagination={false}
            columns={[
              { title: "任务", dataIndex: "task_name" },
              { title: "类型", dataIndex: "task_kind" },
              { title: "状态", dataIndex: "status" },
              { title: "开始时间", dataIndex: "started_at", render: formatDateTime },
              { title: "结束时间", dataIndex: "finished_at", render: formatDateTime },
            ]}
          />
        </Space>
      </Card>
    </div>
  );
}
