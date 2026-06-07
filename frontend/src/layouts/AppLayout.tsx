import {
  ApiOutlined,
  BarChartOutlined,
  DashboardOutlined,
  RobotOutlined,
  SettingOutlined,
  ClusterOutlined,
  FileSearchOutlined,
  UsergroupAddOutlined,
} from "@ant-design/icons";
import { Layout, Menu, Select, Space, Typography, Button } from "antd";
import { useMemo } from "react";
import { Link, useLocation } from "react-router-dom";
import { useAuth } from "../store/auth";

const { Header, Sider, Content } = Layout;
const { Title, Text } = Typography;

const navItems = [
  { key: "/", icon: <DashboardOutlined />, label: <Link to="/">总览</Link> },
  { key: "/tenants", icon: <ClusterOutlined />, label: <Link to="/tenants">租户管理</Link> },
  { key: "/ops", icon: <ApiOutlined />, label: <Link to="/ops">统一运营台</Link> },
  { key: "/members", icon: <UsergroupAddOutlined />, label: <Link to="/members">成员管理</Link> },
  { key: "/analytics", icon: <BarChartOutlined />, label: <Link to="/analytics">数据观测</Link> },
  { key: "/system", icon: <DashboardOutlined />, label: <Link to="/system">系统监控</Link> },
  { key: "/audit", icon: <FileSearchOutlined />, label: <Link to="/audit">审计日志</Link> },
  { key: "/ai-reply", icon: <RobotOutlined />, label: <Link to="/ai-reply">AI 配置</Link> },
  { key: "/settings", icon: <SettingOutlined />, label: <Link to="/settings">系统设置</Link> },
];

export function AppLayout({ children }: { children: React.ReactNode }) {
  const location = useLocation();
  const { user, activeTenant, setActiveTenantById, logout } = useAuth();

  const selectedKey = useMemo(() => {
    const item = navItems.find((entry) => entry.key !== "/" && location.pathname.startsWith(entry.key));
    return item?.key || "/";
  }, [location.pathname]);

  return (
    <Layout className="app-shell">
      <Sider breakpoint="lg" collapsedWidth={0} width={256} className="app-sider">
        <div className="brand-block">
          <div className="brand-mark">B</div>
          <div>
            <Title level={4} className="brand-title">
              Bilibili Ops
            </Title>
            <Text className="brand-subtitle">评论监控与人工回复</Text>
          </div>
        </div>
        <Menu theme="light" mode="inline" selectedKeys={[selectedKey]} items={navItems} />
      </Sider>
      <Layout>
        <Header className="app-header">
          <Space size="large" wrap>
            <div>
              <Text type="secondary">当前用户</Text>
              <div>{user?.display_name}</div>
            </div>
            <div>
              <Text type="secondary">租户</Text>
              <div>
                <Select
                  value={activeTenant?.tenant_id}
                  style={{ minWidth: 220 }}
                  options={(user?.memberships || []).map((item) => ({
                    label: `${item.tenant_name} · ${item.role}`,
                    value: item.tenant_id,
                  }))}
                  onChange={(value) => setActiveTenantById(value)}
                />
              </div>
            </div>
            <Button onClick={logout}>退出登录</Button>
          </Space>
        </Header>
        <Content className="app-content">{children}</Content>
      </Layout>
    </Layout>
  );
}
