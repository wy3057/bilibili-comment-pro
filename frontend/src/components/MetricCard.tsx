import { Card, Statistic } from "antd";

export function MetricCard({
  title,
  value,
  suffix,
}: {
  title: string;
  value: string | number;
  suffix?: string;
}) {
  return (
    <Card>
      <Statistic title={title} value={value} suffix={suffix} />
    </Card>
  );
}

