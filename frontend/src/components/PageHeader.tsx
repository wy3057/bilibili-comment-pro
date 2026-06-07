import { Space, Typography } from "antd";

const { Title, Paragraph } = Typography;

export function PageHeader({ title, description }: { title: string; description: string }) {
  return (
    <Space direction="vertical" size={0} style={{ marginBottom: 20 }}>
      <Title level={2} style={{ marginBottom: 8 }}>
        {title}
      </Title>
      <Paragraph type="secondary" style={{ marginBottom: 0 }}>
        {description}
      </Paragraph>
    </Space>
  );
}

