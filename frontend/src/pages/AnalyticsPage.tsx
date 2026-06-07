import { Card, Col, Row, Table } from "antd";
import { useEffect, useState } from "react";
import { fetchAccountHealth, fetchCommentTrends, fetchReplyPerformance } from "../api/endpoints";
import { PageHeader } from "../components/PageHeader";
import { useAuth } from "../store/auth";
import type { AccountHealthItem, ReplyPerformancePoint, TrendPoint } from "../types/api";
import { useTenantRealtime } from "../utils/realtime";

export function AnalyticsPage() {
  const { token, activeTenant } = useAuth();
  const [commentTrends, setCommentTrends] = useState<TrendPoint[]>([]);
  const [replyTrends, setReplyTrends] = useState<ReplyPerformancePoint[]>([]);
  const [health, setHealth] = useState<AccountHealthItem[]>([]);
  const realtimeVersion = useTenantRealtime(token, activeTenant?.tenant_id);

  useEffect(() => {
    async function load() {
      if (!token || !activeTenant) return;
      const [comments, replies, accounts] = await Promise.all([
        fetchCommentTrends(token, activeTenant.tenant_id),
        fetchReplyPerformance(token, activeTenant.tenant_id),
        fetchAccountHealth(token, activeTenant.tenant_id),
      ]);
      setCommentTrends(comments);
      setReplyTrends(replies);
      setHealth(accounts);
    }
    load().catch(console.error);
  }, [token, activeTenant, realtimeVersion]);

  return (
    <div>
      <PageHeader title="数据观测" description="查看评论趋势、回复趋势与账号层级健康状态。" />
      <Row gutter={[16, 16]}>
        <Col xs={24} xl={12}>
          <Card title="评论趋势">
            <Table
              rowKey="day"
              dataSource={commentTrends}
              pagination={false}
              columns={[
                { title: "日期", dataIndex: "day" },
                { title: "总评论", dataIndex: "comments" },
                { title: "B站评论", dataIndex: "bilibili_comments" },
                { title: "抖音评论", dataIndex: "douyin_comments" },
                { title: "总回复", dataIndex: "replies" },
              ]}
            />
          </Card>
        </Col>
        <Col xs={24} xl={12}>
          <Card title="账号健康">
            <Table
              rowKey="account_id"
              dataSource={health}
              pagination={false}
              columns={[
                { title: "平台", dataIndex: "platform" },
                { title: "账号", dataIndex: "username" },
                { title: "状态", dataIndex: "status" },
                {
                  title: "风控",
                  dataIndex: "risk_status",
                  render: (value?: string | null) => value || "-",
                },
                { title: "待处理评论", dataIndex: "pending_comments" },
              ]}
            />
          </Card>
        </Col>
      </Row>
      <Card title="回复表现" style={{ marginTop: 16 }}>
        <Table
          rowKey="day"
          dataSource={replyTrends}
          pagination={false}
          columns={[
            { title: "日期", dataIndex: "day" },
            { title: "总成功", dataIndex: "sent" },
            { title: "B站成功", dataIndex: "bilibili_sent" },
            { title: "抖音成功", dataIndex: "douyin_sent" },
            { title: "总失败", dataIndex: "failed" },
            { title: "B站失败", dataIndex: "bilibili_failed" },
            { title: "抖音失败", dataIndex: "douyin_failed" },
            {
              title: "平均响应时长",
              dataIndex: "avg_response_minutes",
              render: (value?: number | null) => (value != null ? `${value} 分钟` : "-"),
            },
          ]}
        />
      </Card>
    </div>
  );
}
