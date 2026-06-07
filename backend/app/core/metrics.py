from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram

HTTP_REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status"],
)
HTTP_REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency",
    ["method", "path"],
)
HTTP_ACTIVE_REQUESTS = Gauge(
    "http_active_requests",
    "Active HTTP requests",
)

COMMENTS_DISCOVERED_TOTAL = Counter(
    "bili_comments_discovered_total",
    "Number of newly discovered comments and sub replies",
    ["kind"],
)
TARGET_POLLS_TOTAL = Counter(
    "bili_target_polls_total",
    "Number of target polling attempts",
    ["status"],
)
TARGETS_SCHEDULED_TOTAL = Counter(
    "bili_targets_scheduled_total",
    "Number of targets scheduled by the beat dispatcher",
)
REPLY_ACTIONS_TOTAL = Counter(
    "bili_reply_actions_total",
    "Reply action execution results",
    ["status"],
)
NOTIFICATION_DELIVERIES_TOTAL = Counter(
    "bili_notification_deliveries_total",
    "Webhook notification delivery results",
    ["provider", "status"],
)
TASK_RUNS_TOTAL = Counter(
    "bili_task_runs_total",
    "Task run results",
    ["task_name", "status"],
)
TASK_RUN_DURATION_SECONDS = Histogram(
    "bili_task_run_duration_seconds",
    "Task run durations",
    ["task_name", "status"],
)
WEBSOCKET_CONNECTIONS = Gauge(
    "bili_websocket_connections",
    "Active websocket connections",
)
QR_LOGIN_EVENTS_TOTAL = Counter(
    "bili_qr_login_events_total",
    "QR login state transitions",
    ["status"],
)

