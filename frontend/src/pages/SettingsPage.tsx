import { Alert, App, Button, Card, Descriptions, Form, Input, Modal, Popconfirm, Select, Space, Switch, Table } from "antd";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { createWebhook, deleteWebhook, fetchWebhooks, testWebhook, updateWebhook } from "../api/endpoints";
import { PageHeader } from "../components/PageHeader";
import { useAuth } from "../store/auth";
import type { WebhookConfig } from "../types/api";

export function SettingsPage() {
  const { message } = App.useApp();
  const { user, activeTenant, token } = useAuth();
  const [items, setItems] = useState<WebhookConfig[]>([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [form] = Form.useForm();

  async function loadWebhooks() {
    if (!token || !activeTenant) return;
    const webhooks = await fetchWebhooks(token, activeTenant.tenant_id);
    setItems(webhooks);
  }

  useEffect(() => {
    loadWebhooks().catch(console.error);
  }, [token, activeTenant]);

  async function onCreateWebhook(values: {
    name: string;
    provider: string;
    webhook_url: string;
    is_enabled: boolean;
  }) {
    if (!token || !activeTenant) return;
    setLoading(true);
    try {
      await createWebhook(token, activeTenant.tenant_id, values);
      setOpen(false);
      form.resetFields();
      await loadWebhooks();
      message.success("Webhook 已创建");
    } catch (error) {
      message.error(error instanceof Error ? error.message : "创建失败");
    } finally {
      setLoading(false);
    }
  }

  async function onToggleWebhook(item: WebhookConfig, isEnabled: boolean) {
    if (!token || !activeTenant) return;
    try {
      await updateWebhook(token, activeTenant.tenant_id, item.id, { is_enabled: isEnabled });
      await loadWebhooks();
      message.success("Webhook 状态已更新");
    } catch (error) {
      message.error(error instanceof Error ? error.message : "更新失败");
    }
  }

  async function onDeleteWebhook(item: WebhookConfig) {
    if (!token || !activeTenant) return;
    try {
      await deleteWebhook(token, activeTenant.tenant_id, item.id);
      await loadWebhooks();
      message.success("Webhook 已删除");
    } catch (error) {
      message.error(error instanceof Error ? error.message : "删除失败");
    }
  }

  async function onTestWebhook(item: WebhookConfig) {
    if (!token || !activeTenant) return;
    try {
      const result = await testWebhook(token, activeTenant.tenant_id, item.id);
      message.success(result.detail);
    } catch (error) {
      message.error(error instanceof Error ? error.message : "测试失败");
    }
  }

  return (
    <div>
      <PageHeader title="系统设置" description="管理租户通知配置与当前操作者上下文。" />
      <Alert type="info" showIcon style={{ marginBottom: 16 }} message="新评论轮询成功后，会向已启用的 webhook 配置推送摘要通知。" />
      <Card>
        <Descriptions column={1}>
          <Descriptions.Item label="当前用户">{user?.display_name}</Descriptions.Item>
          <Descriptions.Item label="当前邮箱">{user?.email}</Descriptions.Item>
          <Descriptions.Item label="当前租户">{activeTenant?.tenant_name}</Descriptions.Item>
          <Descriptions.Item label="租户角色">{activeTenant?.role}</Descriptions.Item>
          <Descriptions.Item label="AI 配置">
            <Button type="link" style={{ padding: 0 }}><Link to="/ai-reply">前往独立 AI 配置页</Link></Button>
          </Descriptions.Item>
        </Descriptions>
      </Card>
      <Card
        title="Webhook 通知配置"
        style={{ marginTop: 16 }}
        extra={<Button type="primary" onClick={() => setOpen(true)}>新增 Webhook</Button>}
      >
        <Table
          rowKey="id"
          dataSource={items}
          pagination={false}
          columns={[
            { title: "名称", dataIndex: "name" },
            { title: "Provider", dataIndex: "provider" },
            {
              title: "启用",
              render: (_, record: WebhookConfig) => (
                <Switch checked={record.is_enabled} onChange={(value) => onToggleWebhook(record, value)} />
              ),
            },
            {
              title: "操作",
              render: (_, record: WebhookConfig) => (
                <Space>
                  <Button size="small" onClick={() => onTestWebhook(record)}>
                    测试
                  </Button>
                  <Popconfirm title="确认删除此 webhook？" onConfirm={() => onDeleteWebhook(record)}>
                    <Button danger size="small">
                      删除
                    </Button>
                  </Popconfirm>
                </Space>
              ),
            },
          ]}
        />
      </Card>
      <Modal title="新增 Webhook" open={open} onCancel={() => setOpen(false)} footer={null}>
        <Form layout="vertical" form={form} onFinish={onCreateWebhook} initialValues={{ provider: "dingtalk", is_enabled: true }}>
          <Form.Item label="名称" name="name" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item label="Provider" name="provider" rules={[{ required: true }]}>
            <Select
              options={[
                { label: "钉钉 / 企业微信", value: "dingtalk" },
                { label: "Slack", value: "slack" },
                { label: "Discord", value: "discord" },
              ]}
            />
          </Form.Item>
          <Form.Item label="Webhook URL" name="webhook_url" rules={[{ required: true }]}>
            <Input.TextArea rows={3} />
          </Form.Item>
          <Form.Item label="启用" name="is_enabled" valuePropName="checked">
            <Switch />
          </Form.Item>
          <Button type="primary" htmlType="submit" block loading={loading}>
            保存
          </Button>
        </Form>
      </Modal>
    </div>
  );
}
