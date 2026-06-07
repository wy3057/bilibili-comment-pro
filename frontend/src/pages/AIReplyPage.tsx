import { Alert, App, Card, Descriptions, Select, Space, Tag, Typography } from "antd";
import { useEffect, useState } from "react";
import { fetchAIReplyStatus, updateAIReplyMode } from "../api/endpoints";
import { PageHeader } from "../components/PageHeader";
import { useAuth } from "../store/auth";
import type { AIReplyStatus } from "../types/api";

const { Text, Paragraph } = Typography;

export function AIReplyPage() {
  const { message } = App.useApp();
  const { user, activeTenant, token } = useAuth();
  const [aiStatus, setAiStatus] = useState<AIReplyStatus | null>(null);

  async function loadAIStatus() {
    if (!token || !activeTenant) return;
    const next = await fetchAIReplyStatus(token, activeTenant.tenant_id);
    setAiStatus(next);
  }

  useEffect(() => {
    loadAIStatus().catch(console.error);
  }, [token, activeTenant]);

  async function onToggleAIReplyMode(mode: string) {
    if (!token || !activeTenant) return;
    try {
      const next = await updateAIReplyMode(token, activeTenant.tenant_id, mode);
      setAiStatus(next);
      message.success("AI 回复模式已更新");
    } catch (error) {
      message.error(error instanceof Error ? error.message : "更新 AI 回复模式失败");
    }
  }

  return (
    <div>
      <PageHeader title="AI 配置" description="单独管理 AI 回复状态、模型信息和发送模式。" />
      <Alert
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
        message="当前页面管理的是租户级 AI 回复开关状态与发送模式。API Key、Base URL、模型默认值仍由后端环境变量提供。"
      />
      <Card>
        <Descriptions column={1}>
          <Descriptions.Item label="当前用户">{user?.display_name}</Descriptions.Item>
          <Descriptions.Item label="当前租户">{activeTenant?.tenant_name}</Descriptions.Item>
          <Descriptions.Item label="启用状态">
            {aiStatus ? (
              <Tag color={aiStatus.enabled ? "green" : "default"}>{aiStatus.enabled ? "已启用" : "未启用"}</Tag>
            ) : (
              "-"
            )}
          </Descriptions.Item>
          <Descriptions.Item label="Provider">{aiStatus?.provider || "-"}</Descriptions.Item>
          <Descriptions.Item label="模型">{aiStatus?.model || "-"}</Descriptions.Item>
          <Descriptions.Item label="API 模式">{aiStatus?.api_mode || "-"}</Descriptions.Item>
          <Descriptions.Item label="Base URL">
            <Paragraph style={{ marginBottom: 0 }} copyable={Boolean(aiStatus?.base_url)}>
              {aiStatus?.base_url || "-"}
            </Paragraph>
          </Descriptions.Item>
        </Descriptions>
      </Card>
      <Card title="回复模式" style={{ marginTop: 16 }}>
        <Space direction="vertical" style={{ width: "100%" }}>
          <Alert
            type={aiStatus?.mode === "direct_send" ? "warning" : "info"}
            showIcon
            message={
              aiStatus?.mode === "direct_send"
                ? "当前模式为 AI 生成后直接发送，触发后会直接调用对应平台回复接口。"
                : "当前模式为 AI 生成建议稿，仍需人工审核并点击发送。"
            }
          />
          <Space align="center">
            <Text type="secondary">发送策略</Text>
            <Select
              value={aiStatus?.mode || "manual_review"}
              style={{ width: 260 }}
              onChange={onToggleAIReplyMode}
              options={[
                { label: "人工审核", value: "manual_review" },
                { label: "直接发送", value: "direct_send" },
              ]}
            />
          </Space>
        </Space>
      </Card>
    </div>
  );
}
