import { App, Button, Card, Form, Input, Modal, Space, Table, Tag } from "antd";
import { useEffect, useState } from "react";
import { createTenant, fetchTenants } from "../api/endpoints";
import { PageHeader } from "../components/PageHeader";
import { useAuth } from "../store/auth";
import type { Tenant } from "../types/api";
import { formatDateTime } from "../utils/format";

type CreateTenantFormValues = {
  name: string;
  slug: string;
  description?: string;
};

export function TenantsPage() {
  const { message } = App.useApp();
  const { token, activeTenant, reloadProfile, setActiveTenantById } = useAuth();
  const [items, setItems] = useState<Tenant[]>([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [form] = Form.useForm<CreateTenantFormValues>();

  async function loadTenants() {
    if (!token) return;
    setItems(await fetchTenants(token));
  }

  useEffect(() => {
    loadTenants().catch(console.error);
  }, [token]);

  async function onCreateTenant(values: CreateTenantFormValues) {
    if (!token) return;
    setLoading(true);
    try {
      const tenant = await createTenant(token, values);
      const profile = await reloadProfile();
      setActiveTenantById(tenant.id, profile?.memberships);
      await loadTenants();
      form.resetFields();
      setOpen(false);
      message.success("租户已创建");
    } catch (error) {
      message.error(error instanceof Error ? error.message : "创建租户失败");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <PageHeader title="租户管理" description="创建新的工作空间，并在不同租户之间切换操作上下文。" />
      <Card
        extra={
          <Button type="primary" onClick={() => setOpen(true)}>
            新建租户
          </Button>
        }
      >
        <Table
          rowKey="id"
          dataSource={items}
          columns={[
            { title: "名称", dataIndex: "name" },
            { title: "Slug", dataIndex: "slug" },
            { title: "说明", dataIndex: "description" },
            {
              title: "状态",
              render: (_, record: Tenant) => (
                <Space>
                  <Tag color={record.is_active ? "green" : "default"}>{record.is_active ? "启用" : "停用"}</Tag>
                  {activeTenant?.tenant_id === record.id ? <Tag color="blue">当前租户</Tag> : null}
                </Space>
              ),
            },
            { title: "创建时间", dataIndex: "created_at", render: formatDateTime },
            {
              title: "操作",
              render: (_, record: Tenant) => (
                <Button size="small" onClick={() => setActiveTenantById(record.id)}>
                  切换
                </Button>
              ),
            },
          ]}
        />
      </Card>
      <Modal title="新建租户" open={open} onCancel={() => setOpen(false)} footer={null}>
        <Form layout="vertical" form={form} onFinish={onCreateTenant}>
          <Form.Item label="名称" name="name" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item label="Slug" name="slug" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item label="说明" name="description">
            <Input.TextArea rows={3} />
          </Form.Item>
          <Button type="primary" htmlType="submit" block loading={loading}>
            创建租户
          </Button>
        </Form>
      </Modal>
    </div>
  );
}
