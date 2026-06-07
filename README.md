# Bilibili Comment Platform

多租户 B 站评论监控与人工回复平台。

## Stack

- Backend: FastAPI + SQLAlchemy + Celery + PostgreSQL + Redis
- Frontend: React + TypeScript + Ant Design + Vite
- Bilibili integration: `Nemo2011/bilibili-api`
- Observability: Prometheus + Grafana + Loki
- Deployment: Docker Compose

## Features

- 邮箱密码登录、租户隔离、成员角色控制
- B 站二维码登录与凭证导入
- 抖音企业应用配置、OAuth/code/token 接入与评论回复
- 抖音个人二维码登录助手、Cookie 导入、评论抓取与评论回复
- 多账号视频目标导入与评论轮询
- 统一跨平台运营台 `/ops`，集中处理账号、目标、评论与回复，并区分抖音企业 / 个人来源
- AI 回复建议生成，支持通过 OpenAI Python SDK 对接自定义兼容 API
- 业务看板、任务运行记录、审计日志、系统监控
- WebSocket 实时状态推送

## Quick Start

```bash
cp .env.example .env
docker compose up --build
```

服务入口：

- Frontend: `http://localhost:4173`
- API: `http://localhost:8000/api`
- API docs: `http://localhost:8000/docs`
- Grafana: `http://localhost:3000`
- Prometheus: `http://localhost:9090`

默认引导账号取自 `.env` 中的 `BOOTSTRAP_*` 配置。

密码哈希默认使用 `pbkdf2_sha256`，这样本地开发和容器环境不依赖 `bcrypt` 本地编译链。

AI 回复功能默认关闭，通过以下环境变量启用：

```bash
AI_REPLY_ENABLED=true
AI_REPLY_PROVIDER=openai
AI_REPLY_API_KEY=your-key
AI_REPLY_BASE_URL=
AI_REPLY_MODEL=gpt-4.1-mini
AI_REPLY_API_MODE=chat_completions
```

抖音个人链路默认关闭，通过以下环境变量启用：

```bash
DOUYIN_PERSONAL_ENABLED=true
DOUYIN_PERSONAL_HELPER_BASE_URL=http://douyin-personal-helper:4300
DOUYIN_PERSONAL_LOGIN_SESSION_TTL_SECONDS=600
DOUYIN_PERSONAL_REQUEST_TIMEOUT_SECONDS=30
DOUYIN_PERSONAL_BROWSER_HEADLESS=true
```

启用后，`docker compose up --build` 会同时启动 `douyin-personal-helper`，用于：

- 抖音 Web 二维码登录助手
- Cookie 运行态规范化
- 个人抖音视频目标解析
- 个人抖音评论抓取与 DOM 级回复尝试

内置供应商预设：

- `openai` -> `https://api.openai.com/v1`
- `qwen` -> `https://dashscope.aliyuncs.com/compatible-mode/v1`
- `volcengine` -> `https://ark.cn-beijing.volces.com/api/v3`
- `deepseek` -> `https://api.deepseek.com`

如果你有自己的 OpenAI 兼容网关，继续手动设置 `AI_REPLY_BASE_URL` 即可覆盖默认值。

## Local Development

后端依赖本地 `vendor/bilibili-api` 副本，而不是运行时再从 GitHub 拉取：

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e ./vendor/bilibili-api
pip install -e './backend[dev]'
```

前端安装：

```bash
cd frontend
npm install
```

也可以直接使用仓库根目录下的 `Makefile`：

```bash
make install-backend
make install-frontend
make test
make build-frontend
make smoke
```

## Docs

- `docs/PACKAGE_GUIDE.md`: packaged delivery contents and startup guidance
- `docs/TESTING.md`: automated and manual verification summary
- `docs/DOUYIN.md`: Douyin integration scope, auth constraints, and usage notes
