import { App, Button, Card, Form, Input, Modal, Select, Space, Switch, Table, Tag } from "antd";
import { useEffect, useState } from "react";
import { createTenantMember, fetchTenantMembers, updateTenantMember } from "../api/endpoints";
import { PageHeader } from "../components/PageHeader";
import { useAuth } from "../store/auth";
import type { TenantMember } from "../types/api";
import { formatDateTime } from "../utils/format";
import { useTenantRealtime } from "../utils/realtime";

type CreateMemberFormValues = {
  email: string;
  display_name?: string;
  password?: string;
  role: string;
};

const roleOptions = [
  { label: "Owner", value: "owner" },
  { label: "Admin", value: "admin" },
  { label: "Operator", value: "operator" },
  { label: "Viewer", value: "viewer" },
];

export function MembersPage() {
  const { message } = App.useApp();
  const { token, activeTenant } = useAuth();
  const [items, setItems] = useState<TenantMember[]>([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [form] = Form.useForm();
  const realtimeVersion = useTenantRealtime(token, activeTenant?.tenant_id);

  async function loadMembers() {
    if (!token || !activeTenant) return;
    setItems(await fetchTenantMembers(token, activeTenant.tenant_id));
  }

  useEffect(() => {
    loadMembers().catch(console.error);
  }, [token, activeTenant, realtimeVersion]);

  async function onCreateMember(values: CreateMemberFormValues) {
    if (!token || !activeTenant) return;
    setLoading(true);
    try {
      await createTenantMember(token, activeTenant.tenant_id, values);
      setOpen(false);
      form.resetFields();
      await loadMembers();
      message.success("成员已创建");
    } catch (error) {
      message.error(error instanceof Error ? error.message : "创建成员失败");
    } finally {
      setLoading(false);
    }
  }

  async function onUpdateMember(member: TenantMember, payload: { role?: string; is_active?: boolean }) {
    if (!token || !activeTenant) return;
    try {
      await updateTenantMember(token, activeTenant.tenant_id, member.id, payload);
      await loadMembers();
      message.success("成员已更新");
    } catch (error) {
      message.error(error instanceof Error ? error.message : "更新成员失败");
    }
  }

  return (
    <div>
      <PageHeader title="成员管理" description="管理租户内系统用户、角色和启停状态。" />
      <Card
        extra={
          <Button type="primary" onClick={() => setOpen(true)}>
            新增成员
          </Button>
        }
      >
        <Table
          rowKey="id"
          dataSource={items}
          columns={[
            { title: "显示名", dataIndex: "user_display_name" },
            { title: "邮箱", dataIndex: "user_email" },
            {
              title: "角色",
              render: (_, record: TenantMember) => (
                <Select
                  size="small"
                  style={{ width: 140 }}
                  value={record.role}
                  options={roleOptions}
                  onChange={(value) => onUpdateMember(record, { role: value })}
                />
              ),
            },
            {
              title: "状态",
              render: (_, record: TenantMember) => (
                <Space>
                  <Tag color={record.is_active ? "green" : "default"}>{record.is_active ? "启用" : "停用"}</Tag>
                  <Switch checked={record.is_active} onChange={(value) => onUpdateMember(record, { is_active: value })} />
                </Space>
              ),
            },
            { title: "加入时间", dataIndex: "created_at", render: formatDateTime },
          ]}
        />
      </Card>
      <Modal title="新增成员" open={open} onCancel={() => setOpen(false)} footer={null}>
        <Form
          layout="vertical"
          form={form}
          initialValues={{ role: "viewer" }}
          onFinish={onCreateMember}
        >
          <Form.Item label="邮箱" name="email" rules={[{ required: true, type: "email" }]}>
            <Input />
          </Form.Item>
          <Form.Item label="显示名" name="display_name">
            <Input />
          </Form.Item>
          <Form.Item label="初始密码" name="password">
            <Input.Password />
          </Form.Item>
          <Form.Item label="角色" name="role" rules={[{ required: true }]}>
            <Select options={roleOptions} />
          </Form.Item>
          <Button type="primary" htmlType="submit" block loading={loading}>
            保存
          </Button>
        </Form>
      </Modal>
    </div>
  );
}
