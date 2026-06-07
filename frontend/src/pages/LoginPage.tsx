import { App, Button, Card, Form, Input, Typography } from "antd";
import { useState } from "react";
import { useAuth } from "../store/auth";

const { Title, Paragraph } = Typography;

export function LoginPage() {
  const { message } = App.useApp();
  const { login } = useAuth();
  const [loading, setLoading] = useState(false);

  async function onFinish(values: { email: string; password: string }) {
    setLoading(true);
    try {
      await login(values.email, values.password);
    } catch (error) {
      message.error(error instanceof Error ? error.message : "登录失败");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="login-shell">
      <div className="login-hero">
        <Title>把脚本升级成平台</Title>
        <Paragraph>
          多租户 B 站评论监控、人工回复、任务观测、账号风控与审计全部集中到一个后台。
        </Paragraph>
      </div>
      <Card className="login-card">
        <Title level={3}>后台登录</Title>
        <Form layout="vertical" onFinish={onFinish}>
          <Form.Item label="邮箱" name="email" rules={[{ required: true }]}>
            <Input placeholder="owner@example.com" />
          </Form.Item>
          <Form.Item label="密码" name="password" rules={[{ required: true }]}>
            <Input.Password placeholder="请输入密码" />
          </Form.Item>
          <Button type="primary" htmlType="submit" block size="large" loading={loading}>
            登录
          </Button>
        </Form>
      </Card>
    </div>
  );
}

