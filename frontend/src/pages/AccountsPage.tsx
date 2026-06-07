import { Alert, App, Button, Card, Form, Image, Input, Modal, Space, Table, Tag, Typography } from "antd";
import { useEffect, useMemo, useState } from "react";
import { checkQrLogin, fetchAccounts, importCredentials, refreshAccount, startQrLogin } from "../api/endpoints";
import { PageHeader } from "../components/PageHeader";
import { useAuth } from "../store/auth";
import type { BilibiliAccount, QrCodeSession, QrCodeStatus } from "../types/api";
import { formatDateTime } from "../utils/format";
import { useTenantRealtime } from "../utils/realtime";

const { Paragraph, Text } = Typography;

type CredentialImportFormValues = {
  sessdata: string;
  bili_jct: string;
  buvid3?: string;
  buvid4?: string;
  dedeuserid?: string;
  ac_time_value?: string;
};

export function AccountsPage() {
  const { message } = App.useApp();
  const { token, activeTenant } = useAuth();
  const [items, setItems] = useState<BilibiliAccount[]>([]);
  const [importOpen, setImportOpen] = useState(false);
  const [qrOpen, setQrOpen] = useState(false);
  const [importForm] = Form.useForm();
  const [qrSession, setQrSession] = useState<QrCodeSession | null>(null);
  const [qrStatus, setQrStatus] = useState<QrCodeStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const realtimeVersion = useTenantRealtime(token, activeTenant?.tenant_id);

  async function loadAccounts() {
    if (!token || !activeTenant) return;
    setItems(await fetchAccounts(token, activeTenant.tenant_id));
  }

  useEffect(() => {
    loadAccounts().catch(console.error);
  }, [token, activeTenant, realtimeVersion]);

  useEffect(() => {
    if (!qrOpen || !qrSession || !token || !activeTenant) return;
    const timer = window.setInterval(async () => {
      try {
        const status = await checkQrLogin(token, activeTenant.tenant_id, qrSession.session_id);
        setQrStatus(status);
        if (status.status === "done") {
          await loadAccounts();
          message.success(`已绑定账号 ${status.username || status.uid}`);
          window.clearInterval(timer);
        }
      } catch (error) {
        console.error(error);
      }
    }, 3000);
    return () => window.clearInterval(timer);
  }, [qrOpen, qrSession, token, activeTenant]);

  const qrImageSrc = useMemo(() => {
    if (!qrSession) return "";
    return `data:image/png;base64,${qrSession.qr_image_base64}`;
  }, [qrSession]);

  async function onStartQrLogin() {
    if (!token || !activeTenant) return;
    setLoading(true);
    try {
      const session = await startQrLogin(token, activeTenant.tenant_id);
      setQrSession(session);
      setQrStatus(null);
      setQrOpen(true);
    } catch (error) {
      message.error(error instanceof Error ? error.message : "无法启动二维码登录");
    } finally {
      setLoading(false);
    }
  }

  async function onCheckQrLogin() {
    if (!token || !activeTenant || !qrSession) return;
    try {
      const status = await checkQrLogin(token, activeTenant.tenant_id, qrSession.session_id);
      setQrStatus(status);
      if (status.status === "done") {
        await loadAccounts();
        message.success(`已绑定账号 ${status.username || status.uid}`);
      }
    } catch (error) {
      message.error(error instanceof Error ? error.message : "轮询二维码状态失败");
    }
  }

  async function onImportCredentials(values: CredentialImportFormValues) {
    if (!token || !activeTenant) return;
    setLoading(true);
    try {
      await importCredentials(token, activeTenant.tenant_id, values);
      setImportOpen(false);
      importForm.resetFields();
      await loadAccounts();
      message.success("凭证导入成功");
    } catch (error) {
      message.error(error instanceof Error ? error.message : "凭证导入失败");
    } finally {
      setLoading(false);
    }
  }

  async function onRefreshAccount(accountId: string) {
    if (!token || !activeTenant) return;
    try {
      await refreshAccount(token, activeTenant.tenant_id, accountId);
      await loadAccounts();
      message.success("账号刷新完成");
    } catch (error) {
      message.error(error instanceof Error ? error.message : "刷新失败");
    }
  }

  return (
    <div>
      <PageHeader title="B站账号管理" description="管理租户下多个 B 站账号的登录状态、风险状态与刷新时间。" />
      <Alert
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
        message="二维码登录和凭证导入接口已接入后端。当前页面先提供账号列表与状态观察，后续可继续加弹窗交互。"
      />
      <Card
        extra={
          <Space>
            <Button loading={loading} onClick={onStartQrLogin}>
              二维码登录
            </Button>
            <Button type="primary" onClick={() => setImportOpen(true)}>
              导入凭证
            </Button>
          </Space>
        }
      >
        <Table
          rowKey="id"
          dataSource={items}
          columns={[
            { title: "昵称", dataIndex: "username" },
            { title: "UID", dataIndex: "uid" },
            {
              title: "账号状态",
              dataIndex: "status",
              render: (value: string) => <Tag color={value === "active" ? "green" : "orange"}>{value}</Tag>,
            },
            {
              title: "风控状态",
              dataIndex: "risk_status",
              render: (value: string) => <Tag color={value === "normal" ? "blue" : "red"}>{value}</Tag>,
            },
            { title: "最近校验", dataIndex: "last_validated_at", render: formatDateTime },
            { title: "最近刷新", dataIndex: "last_refreshed_at", render: formatDateTime },
            { title: "最近错误", dataIndex: "last_error" },
            {
              title: "操作",
              render: (_, record: BilibiliAccount) => (
                <Button size="small" onClick={() => onRefreshAccount(record.id)}>
                  刷新凭证
                </Button>
              ),
            },
          ]}
        />
      </Card>
      <Modal
        title="导入 B站凭证"
        open={importOpen}
        onCancel={() => setImportOpen(false)}
        footer={null}
        destroyOnClose
      >
        <Form layout="vertical" form={importForm} onFinish={onImportCredentials}>
          <Form.Item label="SESSDATA" name="sessdata" rules={[{ required: true }]}>
            <Input.TextArea rows={2} />
          </Form.Item>
          <Form.Item label="bili_jct" name="bili_jct" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item label="buvid3" name="buvid3">
            <Input />
          </Form.Item>
          <Form.Item label="buvid4" name="buvid4">
            <Input />
          </Form.Item>
          <Form.Item label="DedeUserID" name="dedeuserid">
            <Input />
          </Form.Item>
          <Form.Item label="ac_time_value" name="ac_time_value">
            <Input.TextArea rows={2} />
          </Form.Item>
          <Button type="primary" htmlType="submit" block loading={loading}>
            导入
          </Button>
        </Form>
      </Modal>
      <Modal
        title="扫码绑定 B站账号"
        open={qrOpen}
        onCancel={() => setQrOpen(false)}
        onOk={onCheckQrLogin}
        okText="检查状态"
      >
        {qrSession && (
          <Space direction="vertical" style={{ width: "100%" }}>
            <Image src={qrImageSrc} alt="QR code" width={240} preview={false} />
            <Paragraph copyable>{qrSession.login_url}</Paragraph>
            <Text type="secondary">状态：{qrStatus?.status || qrSession.status}</Text>
            {qrStatus?.detail ? <Text>{qrStatus.detail}</Text> : null}
          </Space>
        )}
      </Modal>
    </div>
  );
}
