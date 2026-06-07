import { App, Button, Card, Form, Input, InputNumber, Modal, Select, Space, Table, Tag } from "antd";
import { useEffect, useState } from "react";
import {
  createTarget,
  fetchAccounts,
  fetchTargetImportPreview,
  fetchTargets,
  importSelectedTargets,
  pollTarget,
} from "../api/endpoints";
import { PageHeader } from "../components/PageHeader";
import { useAuth } from "../store/auth";
import type { BilibiliAccount, ImportedTargetCandidate, MonitorTarget } from "../types/api";
import { formatDateTime } from "../utils/format";
import { useTenantRealtime } from "../utils/realtime";

type CreateTargetFormValues = {
  account_id: string;
  oid: number;
  bvid: string;
  title: string;
  owner_mid?: number;
  poll_interval?: number;
};

type ImportTargetFormValues = {
  account_id: string;
  poll_interval?: number;
};

export function TargetsPage() {
  const { message } = App.useApp();
  const { token, activeTenant } = useAuth();
  const [items, setItems] = useState<MonitorTarget[]>([]);
  const [accounts, setAccounts] = useState<BilibiliAccount[]>([]);
  const [createOpen, setCreateOpen] = useState(false);
  const [importOpen, setImportOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [importLoading, setImportLoading] = useState(false);
  const [candidates, setCandidates] = useState<ImportedTargetCandidate[]>([]);
  const [selectedCandidateKeys, setSelectedCandidateKeys] = useState<React.Key[]>([]);
  const [createForm] = Form.useForm();
  const [importForm] = Form.useForm<ImportTargetFormValues>();
  const realtimeVersion = useTenantRealtime(token, activeTenant?.tenant_id);

  async function loadData() {
    if (!token || !activeTenant) return;
    const [targets, accountRows] = await Promise.all([
      fetchTargets(token, activeTenant.tenant_id),
      fetchAccounts(token, activeTenant.tenant_id),
    ]);
    setItems(targets);
    setAccounts(accountRows);
  }

  useEffect(() => {
    loadData().catch(console.error);
  }, [token, activeTenant, realtimeVersion]);

  async function onCreateTarget(values: CreateTargetFormValues) {
    if (!token || !activeTenant) return;
    setLoading(true);
    try {
      await createTarget(token, activeTenant.tenant_id, {
        account_id: values.account_id,
        oid: values.oid,
        bvid: values.bvid,
        title: values.title,
        owner_mid: values.owner_mid,
        poll_interval: values.poll_interval || 300,
      });
      setCreateOpen(false);
      createForm.resetFields();
      await loadData();
      message.success("目标已添加");
    } catch (error) {
      message.error(error instanceof Error ? error.message : "添加目标失败");
    } finally {
      setLoading(false);
    }
  }

  async function onImportTargets(values: ImportTargetFormValues) {
    if (!token || !activeTenant) return;
    setImportLoading(true);
    try {
      const created = await importSelectedTargets(token, activeTenant.tenant_id, values.account_id, {
        only_missing: true,
        selected_bvids: selectedCandidateKeys.map(String),
        poll_interval: values.poll_interval || 300,
      });
      setImportOpen(false);
      importForm.resetFields();
      setCandidates([]);
      setSelectedCandidateKeys([]);
      await loadData();
      message.success(`导入 ${created.length} 个目标`);
    } catch (error) {
      message.error(error instanceof Error ? error.message : "导入目标失败");
    } finally {
      setImportLoading(false);
    }
  }

  async function onPreviewImport(accountId: string) {
    if (!token || !activeTenant) return;
    setImportLoading(true);
    try {
      const rows = await fetchTargetImportPreview(token, activeTenant.tenant_id, accountId);
      setCandidates(rows);
      setSelectedCandidateKeys(rows.filter((item) => !item.already_monitored).map((item) => item.bvid));
    } catch (error) {
      message.error(error instanceof Error ? error.message : "加载候选稿件失败");
    } finally {
      setImportLoading(false);
    }
  }

  async function onPollTarget(targetId: string) {
    if (!token || !activeTenant) return;
    try {
      const result = await pollTarget(token, activeTenant.tenant_id, targetId);
      message.success(`轮询完成：新增 ${result.created + result.sub_replies} 条评论/回复`);
      await loadData();
    } catch (error) {
      message.error(error instanceof Error ? error.message : "轮询失败");
    }
  }

  return (
    <div>
      <PageHeader title="监控目标" description="维护要被轮询的稿件列表、轮询间隔和当前启停状态。" />
      <Card
        extra={
          <Space>
            <Button onClick={() => setCreateOpen(true)}>手动添加</Button>
            <Button type="primary" onClick={() => setImportOpen(true)}>
              从账号导入
            </Button>
          </Space>
        }
      >
        <Table
          rowKey="id"
          dataSource={items}
          columns={[
            { title: "标题", dataIndex: "title" },
            { title: "BVID", dataIndex: "bvid" },
            { title: "OID", dataIndex: "oid" },
            {
              title: "状态",
              dataIndex: "status",
              render: (value: string) => <Tag color={value === "active" ? "green" : "default"}>{value}</Tag>,
            },
            { title: "轮询间隔", dataIndex: "poll_interval", render: (value: number) => `${value}s` },
            { title: "最近轮询", dataIndex: "last_polled_at", render: formatDateTime },
            {
              title: "操作",
              render: (_, record: MonitorTarget) => (
                <Button size="small" onClick={() => onPollTarget(record.id)}>
                  立即轮询
                </Button>
              ),
            },
          ]}
        />
      </Card>
      <Modal title="手动添加监控目标" open={createOpen} onCancel={() => setCreateOpen(false)} footer={null}>
        <Form layout="vertical" form={createForm} onFinish={onCreateTarget}>
          <Form.Item label="B站账号" name="account_id" rules={[{ required: true }]}>
            <Select
              options={accounts.map((item) => ({ label: `${item.username} (${item.uid})`, value: item.id }))}
            />
          </Form.Item>
          <Form.Item label="OID/AID" name="oid" rules={[{ required: true }]}>
            <InputNumber style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item label="BVID" name="bvid" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item label="标题" name="title" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item label="UP主 MID" name="owner_mid">
            <InputNumber style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item label="轮询间隔（秒）" name="poll_interval" initialValue={300}>
            <InputNumber style={{ width: "100%" }} min={30} />
          </Form.Item>
          <Button type="primary" htmlType="submit" block loading={loading}>
            添加
          </Button>
        </Form>
      </Modal>
      <Modal
        title="从账号导入目标"
        open={importOpen}
        onCancel={() => {
          setImportOpen(false);
          setCandidates([]);
          setSelectedCandidateKeys([]);
        }}
        footer={null}
        width={900}
      >
        <Form layout="vertical" form={importForm} onFinish={onImportTargets}>
          <Form.Item label="选择账号" name="account_id" rules={[{ required: true }]}>
            <Select
              options={accounts.map((item) => ({ label: `${item.username} (${item.uid})`, value: item.id }))}
              onChange={(value) => onPreviewImport(String(value))}
            />
          </Form.Item>
          <Form.Item label="导入后的轮询间隔（秒）" name="poll_interval" initialValue={300}>
            <InputNumber style={{ width: "100%" }} min={30} />
          </Form.Item>
          <Table
            rowKey="bvid"
            loading={importLoading}
            pagination={false}
            dataSource={candidates}
            rowSelection={{
              selectedRowKeys: selectedCandidateKeys,
              onChange: setSelectedCandidateKeys,
              getCheckboxProps: (record) => ({
                disabled: record.already_monitored,
              }),
            }}
            columns={[
              { title: "标题", dataIndex: "title" },
              { title: "BVID", dataIndex: "bvid" },
              { title: "OID", dataIndex: "oid" },
              {
                title: "状态",
                render: (_, record: ImportedTargetCandidate) => (
                  <Tag color={record.already_monitored ? "blue" : "green"}>
                    {record.already_monitored ? "已在监控中" : "可导入"}
                  </Tag>
                ),
              },
            ]}
            style={{ marginBottom: 16 }}
          />
          <Button
            type="primary"
            htmlType="submit"
            block
            loading={importLoading}
            disabled={selectedCandidateKeys.length === 0}
          >
            导入已选稿件
          </Button>
        </Form>
      </Modal>
    </div>
  );
}
